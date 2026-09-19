"""
Unit tests for policies.engine.PolicyEngine.

Also cross-checks DEFAULT_ROLE_PERMISSIONS against the schema.sql seed
data conceptually: every permission code referenced must be a permission
the tool catalog actually maps to (via permission_map), catching typos
that would otherwise silently deny everyone.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from policies.default_roles import DEFAULT_ROLE_PERMISSIONS  # noqa: E402
from policies.engine import PolicyEngine  # noqa: E402
from policies.permission_map import TOOL_PERMISSION_MAP  # noqa: E402


class TestPolicyEngineDefaults:
    def setup_method(self):
        self.engine = PolicyEngine()

    def test_admin_can_use_any_tool(self):
        for tool_name in TOOL_PERMISSION_MAP:
            decision = self.engine.evaluate("admin", tool_name)
            assert decision["allowed"] is True, tool_name

    def test_analyst_can_read_database(self):
        decision = self.engine.evaluate("analyst", "database.query")
        assert decision["allowed"] is True

    def test_analyst_cannot_send_email(self):
        decision = self.engine.evaluate("analyst", "gmail.send")
        assert decision["allowed"] is False
        assert "email.send" in decision["reason"]

    def test_unexposed_database_write_is_not_a_policy_tool(self):
        # The PostgreSQL MCP surface is intentionally read-only.  Write/delete
        # permission codes are reserved for a future explicitly gated MCP tool,
        # but must not appear as executable tools before that surface exists.
        with pytest.raises(KeyError):
            self.engine.evaluate("analyst", "database.update")

    def test_manager_can_send_email(self):
        decision = self.engine.evaluate("manager", "gmail.send")
        assert decision["allowed"] is True

    def test_support_agent_cannot_send_email(self):
        # support_agent can draft but not send, per the seed data.
        decision = self.engine.evaluate("support_agent", "gmail.send")
        assert decision["allowed"] is False

    def test_support_agent_can_draft_email(self):
        decision = self.engine.evaluate("support_agent", "gmail.draft")
        assert decision["allowed"] is True

    def test_unknown_role_is_denied(self):
        decision = self.engine.evaluate("intern_with_no_role", "drive.search")
        assert decision["allowed"] is False

    def test_decision_carries_risk_metadata_regardless_of_outcome(self):
        allowed = self.engine.evaluate("admin", "gmail.send")
        denied = self.engine.evaluate("analyst", "gmail.send")
        assert allowed["risk_level"] == denied["risk_level"] == "HIGH"
        assert allowed["requires_approval"] == denied["requires_approval"] is True


class TestPolicyEngineWithCustomRoles:
    def test_custom_role_permissions_are_respected(self):
        engine = PolicyEngine(role_permissions={"intern": {"files.read"}})
        assert engine.evaluate("intern", "drive.search")["allowed"] is True
        assert engine.evaluate("intern", "database.query")["allowed"] is False


class TestSeedDataConsistency:
    def test_every_granted_permission_is_a_real_permission_code(self):
        known_permission_codes = set(TOOL_PERMISSION_MAP.values())
        for role, permissions in DEFAULT_ROLE_PERMISSIONS.items():
            unknown = permissions - known_permission_codes
            # Some permission codes are intentionally reserved before an
            # executable tool surface exists. CRM has no MCP server yet, and
            # database.write/delete are deliberately not exposed by the
            # read-only PostgreSQL MCP server.
            reserved = {"database.write", "database.delete"}
            unknown = {
                p for p in unknown
                if not p.startswith("crm.") and p not in reserved
            }
            assert not unknown, f"Role '{role}' granted unmapped permissions: {unknown}"
