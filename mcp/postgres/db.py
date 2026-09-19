"""
Connection pool management for the PostgreSQL MCP server.

The pool should connect using a database role that is granted SELECT-only
privileges in production. This server enforces read-only queries in
tools.py as a coarse safety net, but the real authorization boundary is
the Policy Engine (Phase 3) sitting in front of the MCP Gateway — this
server should never be reachable directly by an agent in production.
"""
import os

import asyncpg

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        dsn = os.environ.get(
            "MCP_POSTGRES_DSN",
            "postgresql://eap:eap_dev_password@postgres:5432/eap",
        )
        _pool = await asyncpg.create_pool(dsn, min_size=1, max_size=5)
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
