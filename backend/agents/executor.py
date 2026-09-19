"""
Executor: runs a single plan step by calling the appropriate MCP tool.

This node does not decide risk policy or approvals — it just executes
whatever step it's given. Risk gating happens in graph.py's routing
functions, before this node is ever reached for a HIGH/CRITICAL step
that hasn't been approved.
"""
from typing import Any

from agents import mcp_client
from agents.sql_safety import normalize_read_only_sql
from agents.state import PlanStep
from agents.tool_catalog import get_tool


def normalize_tool_arguments(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Map logical planner arguments to the concrete MCP tool contract."""
    mapped = dict(arguments)
    if tool_name == "database.query":
        candidate = mapped.get("sql", mapped.get("query"))
        if not isinstance(candidate, str):
            raise ValueError("database.query requires a valid read-only SQL SELECT in 'sql'")
        return {"sql": normalize_read_only_sql(candidate)}
    if tool_name == "database.describe_table" and "table_name" not in mapped and "table" in mapped:
        return {"table_name": mapped["table"]}
    return mapped


async def execute_step(step: PlanStep) -> Any:
    """
    Execute a single step and return its raw result.

    Raises on failure — the caller (executor_node in graph.py) is
    responsible for catching the exception and recording it in
    WorkflowState.errors so the Verifier/Recovery nodes can react to it.
    """
    entry = get_tool(step["tool_name"])
    arguments = normalize_tool_arguments(step["tool_name"], step["arguments"])
    return await mcp_client.call_tool(entry["mcp_server"], entry["mcp_tool"], arguments)
