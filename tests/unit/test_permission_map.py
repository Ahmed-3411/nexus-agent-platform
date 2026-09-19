"""Unit tests for policies.permission_map."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from agents.tool_catalog import TOOL_CATALOG  # noqa: E402
from policies.permission_map import TOOL_PERMISSION_MAP, required_permission  # noqa: E402


class TestPermissionMap:
    def test_every_tool_in_catalog_has_a_permission_mapping(self):
        missing = set(TOOL_CATALOG) - set(TOOL_PERMISSION_MAP)
        assert not missing, f"Tools missing a permission mapping: {missing}"

    def test_required_permission_returns_mapped_code(self):
        assert required_permission("gmail.send") == "email.send"

    def test_unknown_tool_raises(self):
        with pytest.raises(KeyError):
            required_permission("not.a.tool")
