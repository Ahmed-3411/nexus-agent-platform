"""
Unit tests for the static tool catalog (Phase 2 stand-in for the real
Policy Engine that lands in Phase 3).
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from agents.tool_catalog import TOOL_CATALOG, catalog_prompt_listing, get_tool  # noqa: E402


class TestGetTool:
    def test_returns_known_tool(self):
        entry = get_tool("database.query")
        assert entry["mcp_server"] == "postgres"
        assert entry["mcp_tool"] == "query_database"
        assert entry["risk_level"] == "LOW"

    def test_raises_for_unknown_tool(self):
        with pytest.raises(KeyError):
            get_tool("not.a.real.tool")


class TestCatalogInvariants:
    def test_send_email_is_high_risk_and_requires_approval(self):
        entry = TOOL_CATALOG["gmail.send"]
        assert entry["risk_level"] == "HIGH"
        assert entry["requires_approval"] is True

    def test_every_low_risk_tool_does_not_require_approval(self):
        for name, entry in TOOL_CATALOG.items():
            if entry["risk_level"] == "LOW":
                assert entry["requires_approval"] is False, name

    def test_every_entry_maps_to_a_known_server(self):
        for name, entry in TOOL_CATALOG.items():
            assert entry["mcp_server"] in {"postgres", "gmail", "drive"}, name


class TestCatalogPromptListing:
    def test_listing_mentions_every_tool_name(self):
        listing = catalog_prompt_listing()
        for name in TOOL_CATALOG:
            assert name in listing
