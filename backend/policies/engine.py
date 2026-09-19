"""
Policy Engine.

Answers exactly one question: given a role and a tool, is this action
allowed? It combines two pieces of information:

  1. What permission does this tool require? (permission_map.py)
  2. Does this role have that permission? (a role -> permissions map,
     defaulting to DEFAULT_ROLE_PERMISSIONS but overridable — see
     PolicyEngine.__init__ and policies/loader.py for the DB-backed
     version)

This is deliberately the ONLY place in the codebase that makes an
allow/deny decision for tool usage. agents/graph.py's risk_check_node
currently only checks requires_approval (Phase 2); wiring risk_check_node
to call PolicyEngine.evaluate() first is the next integration step once
the API layer carries an authenticated user's role into the graph run.
"""
from typing import TypedDict

from agents.state import RiskLevel
from agents.tool_catalog import get_tool
from policies.default_roles import DEFAULT_ROLE_PERMISSIONS
from policies.permission_map import required_permission


class PolicyDecision(TypedDict):
    allowed: bool
    reason: str
    risk_level: RiskLevel
    requires_approval: bool
    required_permission: str


class PolicyEngine:
    def __init__(self, role_permissions: dict[str, set[str]] | None = None):
        """
        `role_permissions` maps role name -> set of granted permission
        codes. Defaults to DEFAULT_ROLE_PERMISSIONS (mirrors the
        schema.sql seed data) for use without a database connection.
        """
        self.role_permissions = role_permissions if role_permissions is not None else DEFAULT_ROLE_PERMISSIONS

    def evaluate(self, role: str, tool_name: str) -> PolicyDecision:
        entry = get_tool(tool_name)
        permission = required_permission(tool_name)
        granted = self.role_permissions.get(role, set())

        if role not in self.role_permissions:
            return PolicyDecision(
                allowed=False,
                reason=f"Unknown role '{role}'.",
                risk_level=entry["risk_level"],
                requires_approval=entry["requires_approval"],
                required_permission=permission,
            )

        if permission not in granted:
            return PolicyDecision(
                allowed=False,
                reason=f"Role '{role}' lacks required permission '{permission}'.",
                risk_level=entry["risk_level"],
                requires_approval=entry["requires_approval"],
                required_permission=permission,
            )

        return PolicyDecision(
            allowed=True,
            reason="Permitted.",
            risk_level=entry["risk_level"],
            requires_approval=entry["requires_approval"],
            required_permission=permission,
        )
