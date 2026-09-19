"""
PostgreSQL MCP server.

Exposes four read-only tools over MCP (using the official `mcp` SDK's
FastMCP helper), served over SSE on MCP_POSTGRES_PORT (default 9101):

    - query_database(sql)      LOW risk
    - get_schema()              LOW risk
    - list_tables()              LOW risk
    - describe_table(table_name) LOW risk

Write/delete operations are intentionally NOT exposed here — see
docs/PHASES.md (Phase 3: Policy Engine / Risk Engine) for where those
belong once they exist.

Run standalone (requires a reachable Postgres instance, see db.py):
    python server.py

Inside docker-compose this file is the container's CMD (see Dockerfile).
"""
import asyncio
import os

from mcp.server.fastmcp import FastMCP

import tools as pg_tools
from db import close_pool, get_pool

PORT = int(os.environ.get("MCP_POSTGRES_PORT", "9101"))

mcp = FastMCP("postgres-mcp", host="0.0.0.0", port=PORT)


@mcp.tool()
async def query_database(sql: str) -> dict:
    """Run a read-only SQL SELECT query against the database and return the rows.

    Only single SELECT (or read-only WITH/CTE) statements are accepted;
    write and DDL statements are rejected before they reach the database.
    """
    pool = await get_pool()
    return await pg_tools.query_database(pool, sql)


@mcp.tool()
async def get_schema() -> dict:
    """Return every table and its columns in the public schema."""
    pool = await get_pool()
    return await pg_tools.get_schema(pool)


@mcp.tool()
async def list_tables() -> dict:
    """List all table names in the public schema."""
    pool = await get_pool()
    return await pg_tools.list_tables(pool)


@mcp.tool()
async def describe_table(table_name: str) -> dict:
    """Describe the columns, types, defaults, and primary key of a single table."""
    pool = await get_pool()
    return await pg_tools.describe_table(pool, table_name)


if __name__ == "__main__":
    print(f"[mcp-postgres] starting on 0.0.0.0:{PORT}")
    try:
        mcp.run(transport="sse")
    finally:
        asyncio.run(close_pool())
