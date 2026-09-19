"""
Unit tests for agents.mcp_client's pure-logic helpers.

call_tool() itself opens a real SSE connection and is exercised by
integration tests (tests/integration), not here.
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from agents import mcp_client  # noqa: E402


class TestServerUrl:
    def test_known_servers_resolve(self):
        assert mcp_client._server_url("postgres") == mcp_client.settings.mcp_postgres_url
        assert mcp_client._server_url("gmail") == mcp_client.settings.mcp_gmail_url
        assert mcp_client._server_url("drive") == mcp_client.settings.mcp_drive_url

    def test_unknown_server_raises(self):
        with pytest.raises(KeyError):
            mcp_client._server_url("not-a-real-server")


class TestParseToolResult:
    def test_parses_json_text_content(self):
        block = MagicMock()
        block.text = '{"rows": [1, 2, 3]}'
        result = MagicMock()
        result.content = [block]

        parsed = mcp_client._parse_tool_result(result)
        assert parsed == {"rows": [1, 2, 3]}

    def test_falls_back_to_raw_text_for_non_json(self):
        block = MagicMock()
        block.text = "plain text, not json"
        result = MagicMock()
        result.content = [block]

        parsed = mcp_client._parse_tool_result(result)
        assert parsed == "plain text, not json"

    def test_returns_none_for_empty_content(self):
        result = MagicMock()
        result.content = []
        assert mcp_client._parse_tool_result(result) is None

    def test_returns_block_when_no_text_attribute(self):
        block = object()  # no `.text` attribute at all
        result = MagicMock()
        result.content = [block]
        assert mcp_client._parse_tool_result(result) is block
