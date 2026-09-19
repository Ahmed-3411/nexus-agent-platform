"""Focused regressions for planner/MCP runtime integration hardening."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from openai import RateLimitError as OpenAIRateLimitError

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from agents import mcp_client, planner  # noqa: E402
from agents import runner  # noqa: E402
from agents.executor import execute_step, normalize_tool_arguments  # noqa: E402
from agents.tool_catalog import TOOL_CATALOG  # noqa: E402


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestPlannerFallback:
    def test_openai_quota_error_uses_deterministic_fallback(self):
        response = httpx.Response(429, request=httpx.Request("POST", "https://api.openai.com/v1/responses"))
        quota_error = OpenAIRateLimitError("insufficient_quota", response=response, body={})
        fake_client = MagicMock()
        fake_client.responses.create.side_effect = quota_error

        with (
            patch.object(planner, "ANTHROPIC_API_KEY", None),
            patch.object(planner, "OPENAI_API_KEY", "test-key"),
            patch.object(planner, "OpenAI", return_value=fake_client),
        ):
            plan = planner.generate_plan("Get the database schema")

        assert plan[0]["tool_name"] == "database.get_schema"
        assert set(plan[0]) == {"step_index", "tool_name", "arguments", "description"}

    def test_missing_provider_keys_uses_catalog_only(self):
        with (
            patch.object(planner, "ANTHROPIC_API_KEY", None),
            patch.object(planner, "OPENAI_API_KEY", None),
        ):
            plan = planner.generate_plan("Show available database tables")

        assert plan[0]["tool_name"] == "database.list_tables"
        assert all(step["tool_name"] in TOOL_CATALOG for step in plan)

    def test_provider_schema_is_normalized_and_query_argument_is_mapped(self):
        plan = planner._parse_plan(
            '{"steps":[{"step_index":99,"tool":"database.query",'
            '"arguments":{"query":"SELECT 1;"},"description":7}]}'
        )
        assert plan == [{
            "step_index": 0,
            "tool_name": "database.query",
            "arguments": {"sql": "SELECT 1"},
            "description": "7",
        }]

    def test_natural_language_database_request_is_not_used_as_sql(self):
        plan = planner._fallback_plan("Find all customers in the database")
        assert plan[0]["tool_name"] == "database.list_tables"
        assert "sql" not in plan[0]["arguments"]


class TestMCPNormalization:
    def test_mcp_string_error_becomes_structured_failure(self):
        result = SimpleNamespace(
            content=[SimpleNamespace(text="Drive credentials are not configured")],
            isError=True,
            structuredContent=None,
            structured_content=None,
        )
        normalized = mcp_client.normalize_tool_result(result, "drive", "search_files")
        assert normalized == {
            "ok": False,
            "error": "Drive credentials are not configured",
            "tool_name": "search_files",
            "server": "drive",
        }

    def test_exception_group_surfaces_leaf_error_and_redacts_secret(self):
        exc = ExceptionGroup(
            "unhandled errors in a TaskGroup",
            [RuntimeError("connection failed api_key=sk-supersecretvalue")],
        )
        message = mcp_client.format_exception(exc)
        assert "TaskGroup" not in message
        assert "connection failed" in message
        assert "supersecretvalue" not in message
        assert "REDACTED" in message


class TestDatabaseArgumentMapping:
    def test_logical_query_maps_to_mcp_sql(self):
        assert normalize_tool_arguments("database.query", {"query": "SELECT 1;"}) == {
            "sql": "SELECT 1"
        }

    @pytest.mark.asyncio
    async def test_executor_calls_query_database_with_sql_parameter(self):
        call = AsyncMock(return_value={"ok": True, "row_count": 1, "rows": [{"value": 1}]})
        step = {
            "step_index": 0,
            "tool_name": "database.query",
            "arguments": {"query": "SELECT 1 AS value"},
            "description": "Read a constant.",
        }
        with patch("agents.executor.mcp_client.call_tool", new=call):
            await execute_step(step)
        call.assert_awaited_once_with("postgres", "query_database", {"sql": "SELECT 1 AS value"})

    @pytest.mark.parametrize("unsafe", ["show me customers", "DELETE FROM users", "SELECT 1; DROP TABLE users"])
    def test_non_sql_and_write_queries_are_rejected(self, unsafe):
        with pytest.raises(ValueError):
            normalize_tool_arguments("database.query", {"query": unsafe})


class TestMissingGoogleCredentials:
    @pytest.mark.parametrize(
        ("module_name", "relative_path", "prefix", "expected"),
        [
            ("_drive_auth_hardening", "mcp/drive/auth.py", "DRIVE", "Drive credentials are not configured"),
            ("_gmail_auth_hardening", "mcp/gmail/auth.py", "GMAIL", "Gmail credentials are not configured"),
        ],
    )
    def test_missing_credentials_raise_clean_actionable_error(
        self, monkeypatch, module_name, relative_path, prefix, expected
    ):
        module = _load_module(module_name, ROOT / relative_path)
        for suffix in ("CLIENT_ID", "CLIENT_SECRET", "REFRESH_TOKEN"):
            monkeypatch.delenv(f"{prefix}_{suffix}", raising=False)
        module.reset_service_cache()
        getter = module.get_drive_service if prefix == "DRIVE" else module.get_gmail_service
        with pytest.raises(RuntimeError, match=expected):
            getter()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("tool_name", "server", "mcp_tool", "message"),
        [
            ("drive.search", "drive", "search_files", "Drive credentials are not configured"),
            ("gmail.search", "gmail", "search_emails", "Gmail credentials are not configured"),
        ],
    )
    async def test_missing_credentials_end_as_visible_failed_workflow(
        self, tool_name, server, mcp_tool, message
    ):
        plan = [{
            "step_index": 0,
            "tool_name": tool_name,
            "arguments": {"query": "invoice"},
            "description": "Credential failure test.",
        }]
        tool_result = {
            "ok": False,
            "error": message,
            "tool_name": mcp_tool,
            "server": server,
        }
        with (
            patch("agents.graph.generate_plan", return_value=plan),
            patch("agents.graph.execute_step", new=AsyncMock(return_value=tool_result)),
        ):
            _, state = await runner.start_workflow("find invoice", role="analyst")

        assert state["status"] == "FAILED"
        assert state["errors"][0] == message
        assert state["verifications"][0]["actual"] == tool_result
        assert message in state["final_result"]["error"]
