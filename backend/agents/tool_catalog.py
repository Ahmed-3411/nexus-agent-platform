"""
Static tool catalog for the Planner and Executor.

This mirrors the `tools` table seed data in backend/db/schema.sql. It is
intentionally hardcoded here for Phase 2 — Phase 3 will move this into
the real Policy Engine, backed by the database, with per-role permission
checks. Until then, this module is the single source of truth for which
tools exist, which MCP server hosts them, and their risk level.

`tool_name` here is the *logical* name used in the Planner's output and
in workflow_steps.tool_name. `mcp_tool` is the actual function name
exposed by the MCP server (see mcp/<server>/server.py).
"""
from typing import TypedDict

from agents.state import RiskLevel


class ToolCatalogEntry(TypedDict):
    mcp_server: str  # one of "postgres", "gmail", "drive"
    mcp_tool: str  # actual tool name on that MCP server
    risk_level: RiskLevel
    requires_approval: bool


TOOL_CATALOG: dict[str, ToolCatalogEntry] = {
    "database.query": {
        "mcp_server": "postgres",
        "mcp_tool": "query_database",
        "risk_level": "LOW",
        "requires_approval": False,
    },
    "database.get_schema": {
        "mcp_server": "postgres",
        "mcp_tool": "get_schema",
        "risk_level": "LOW",
        "requires_approval": False,
    },
    "database.list_tables": {
        "mcp_server": "postgres",
        "mcp_tool": "list_tables",
        "risk_level": "LOW",
        "requires_approval": False,
    },
    "database.describe_table": {
        "mcp_server": "postgres",
        "mcp_tool": "describe_table",
        "risk_level": "LOW",
        "requires_approval": False,
    },
    "gmail.search": {
        "mcp_server": "gmail",
        "mcp_tool": "search_emails",
        "risk_level": "LOW",
        "requires_approval": False,
    },
    "gmail.read": {
        "mcp_server": "gmail",
        "mcp_tool": "read_email",
        "risk_level": "MEDIUM",
        "requires_approval": False,
    },
    "gmail.draft": {
        "mcp_server": "gmail",
        "mcp_tool": "draft_email",
        "risk_level": "MEDIUM",
        "requires_approval": False,
    },
    "gmail.send": {
        "mcp_server": "gmail",
        "mcp_tool": "send_email",
        "risk_level": "HIGH",
        "requires_approval": True,
    },
    "drive.search": {
        "mcp_server": "drive",
        "mcp_tool": "search_files",
        "risk_level": "LOW",
        "requires_approval": False,
    },
    "drive.list": {
        "mcp_server": "drive",
        "mcp_tool": "list_files",
        "risk_level": "LOW",
        "requires_approval": False,
    },
    "drive.read": {
        "mcp_server": "drive",
        "mcp_tool": "read_file",
        "risk_level": "LOW",
        "requires_approval": False,
    },
}


def get_tool(tool_name: str) -> ToolCatalogEntry:
    if tool_name not in TOOL_CATALOG:
        raise KeyError(f"Unknown tool '{tool_name}'. Not in TOOL_CATALOG.")
    return TOOL_CATALOG[tool_name]


def catalog_prompt_listing() -> str:
    """Render the catalog as a human-readable list for the Planner's system prompt."""
    lines = []
    for name, entry in TOOL_CATALOG.items():
        lines.append(f"- {name} (server: {entry['mcp_server']}, risk: {entry['risk_level']})")
    return "\n".join(lines)
