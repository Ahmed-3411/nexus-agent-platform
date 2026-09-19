"""
Tool -> required permission mapping.

This is the missing link between agents/tool_catalog.py (which tool
exists, which MCP server hosts it, its risk level) and the RBAC tables
in backend/db/schema.sql (which permission codes each role has been
granted). The Policy Engine uses this map to answer: "does this role
have the permission this tool requires?"

Keep this in sync with:
  - the `permissions.code` seed rows in backend/db/schema.sql
  - the `tool_name` keys in agents/tool_catalog.TOOL_CATALOG
"""

TOOL_PERMISSION_MAP: dict[str, str] = {
    "database.query": "database.read",
    "database.get_schema": "database.read",
    "database.list_tables": "database.read",
    "database.describe_table": "database.read",
    "gmail.search": "email.read",
    "gmail.read": "email.read",
    "gmail.draft": "email.draft",
    "gmail.send": "email.send",
    "drive.search": "files.read",
    "drive.list": "files.read",
    "drive.read": "files.read",
}


def required_permission(tool_name: str) -> str:
    if tool_name not in TOOL_PERMISSION_MAP:
        raise KeyError(f"No permission mapping defined for tool '{tool_name}'.")
    return TOOL_PERMISSION_MAP[tool_name]


def required_permission_or_none(tool_name: str) -> str | None:
    """Same as required_permission(), but returns None instead of raising for an unmapped tool."""
    return TOOL_PERMISSION_MAP.get(tool_name)
