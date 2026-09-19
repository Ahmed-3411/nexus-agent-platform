"""
Unit tests for the Planner.

`parse_plan_response` is tested directly with hand-written JSON strings.
`generate_plan` is tested with a fake Anthropic client so no API key or
network access is needed.
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from agents.planner import PlanValidationError, generate_plan, parse_plan_response  # noqa: E402


class TestParsePlanResponse:
    def test_parses_valid_plan(self):
        text = '[{"tool_name": "database.query", "arguments": {"sql": "SELECT 1"}}]'
        plan = parse_plan_response(text)
        assert len(plan) == 1
        assert plan[0]["tool_name"] == "database.query"
        assert plan[0]["step_index"] == 0
        assert plan[0]["arguments"] == {"sql": "SELECT 1"}

    def test_strips_markdown_code_fences(self):
        text = '```json\n[{"tool_name": "drive.search", "arguments": {"query": "report"}}]\n```'
        plan = parse_plan_response(text)
        assert plan[0]["tool_name"] == "drive.search"

    def test_empty_plan_is_valid(self):
        assert parse_plan_response("[]") == []

    def test_assigns_sequential_step_indices(self):
        text = (
            '[{"tool_name": "drive.search", "arguments": {}}, '
            '{"tool_name": "drive.read", "arguments": {}}]'
        )
        plan = parse_plan_response(text)
        assert [s["step_index"] for s in plan] == [0, 1]

    def test_rejects_invalid_json(self):
        with pytest.raises(PlanValidationError):
            parse_plan_response("not json at all")

    def test_rejects_non_array_json(self):
        with pytest.raises(PlanValidationError):
            parse_plan_response('{"tool_name": "drive.search"}')

    def test_rejects_unknown_tool(self):
        with pytest.raises(PlanValidationError):
            parse_plan_response('[{"tool_name": "database.drop_everything", "arguments": {}}]')

    def test_rejects_missing_tool_name(self):
        with pytest.raises(PlanValidationError):
            parse_plan_response('[{"arguments": {}}]')

    def test_rejects_non_object_arguments(self):
        with pytest.raises(PlanValidationError):
            parse_plan_response('[{"tool_name": "drive.search", "arguments": "oops"}]')

    def test_defaults_missing_arguments_to_empty_dict(self):
        plan = parse_plan_response('[{"tool_name": "drive.search"}]')
        assert plan[0]["arguments"] == {}


def _make_fake_anthropic_client(response_text: str):
    fake_block = MagicMock()
    fake_block.text = response_text
    fake_response = MagicMock()
    fake_response.content = [fake_block]

    client = MagicMock()
    client.messages.create.return_value = fake_response
    return client


class TestGeneratePlan:
    def test_returns_parsed_plan_from_client_response(self):
        client = _make_fake_anthropic_client(
            '[{"tool_name": "gmail.search", "arguments": {"query": "invoice"}}]'
        )
        plan = generate_plan("find invoice emails", client=client)
        assert plan[0]["tool_name"] == "gmail.search"
        client.messages.create.assert_called_once()

    def test_propagates_validation_errors(self):
        client = _make_fake_anthropic_client('[{"tool_name": "not.a.tool"}]')
        with pytest.raises(PlanValidationError):
            generate_plan("do something unsupported", client=client)
