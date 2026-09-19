"""
Tool implementations for the PostgreSQL MCP server.

All four tools here are LOW risk by design: strictly read-only. Write and
delete operations are intentionally NOT exposed by this MCP server — those
belong behind a separate, higher-risk tool surface gated explicitly by the
Policy Engine and Risk Engine (Phase 3), never available through a plain
query string.

The `_assert_read_only` guard below is a coarse, defense-in-depth safety
net at the tool layer. It is NOT a substitute for real authorization —
the MCP Gateway + Policy Engine (Phase 3) is the actual enforcement point,
and the database role this pool connects with should also be SELECT-only
at the Postgres GRANT level.
"""
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import asyncpg

_FORBIDDEN_KEYWORDS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|GRANT|REVOKE|CREATE|MERGE)\b",
    re.IGNORECASE,
)


class NotReadOnlyError(ValueError):
    """Raised when a requested query attempts a write/DDL operation."""


def _assert_read_only(sql: str) -> None:
    stripped = sql.strip().rstrip(";")
    if not stripped:
        raise ValueError("Empty SQL statement.")
    if ";" in stripped:
        raise ValueError("Multiple statements in a single call are not allowed.")
    if not stripped.upper().startswith(("SELECT", "WITH")):
        raise NotReadOnlyError("Only SELECT (or read-only WITH/CTE) statements are permitted.")
    if _FORBIDDEN_KEYWORDS.search(stripped):
        raise NotReadOnlyError("Statement contains a forbidden write/DDL keyword.")


async def query_database(pool: "asyncpg.Pool", sql: str, row_limit: int = 500) -> dict[str, Any]:
    """
    Run a read-only SQL query and return the resulting rows.

    Risk level: LOW.
    """
    _assert_read_only(sql)
    async with pool.acquire() as conn:
        records = await conn.fetch(sql)
    rows = [dict(r) for r in records[:row_limit]]
    return {
        "row_count": len(rows),
        "truncated": len(records) > row_limit,
        "rows": rows,
    }


async def get_schema(pool: "asyncpg.Pool") -> dict[str, Any]:
    """
    Return every table and its columns in the public schema.

    Risk level: LOW.
    """
    query = """
        SELECT table_name, column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_schema = 'public'
        ORDER BY table_name, ordinal_position;
    """
    async with pool.acquire() as conn:
        records = await conn.fetch(query)

    schema: dict[str, list[dict[str, Any]]] = {}
    for r in records:
        schema.setdefault(r["table_name"], []).append(
            {
                "column": r["column_name"],
                "type": r["data_type"],
                "nullable": r["is_nullable"] == "YES",
            }
        )
    return {"tables": schema}


async def list_tables(pool: "asyncpg.Pool") -> dict[str, Any]:
    """
    List all table names in the public schema.

    Risk level: LOW.
    """
    query = """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY table_name;
    """
    async with pool.acquire() as conn:
        records = await conn.fetch(query)
    return {"tables": [r["table_name"] for r in records]}


async def describe_table(pool: "asyncpg.Pool", table_name: str) -> dict[str, Any]:
    """
    Describe columns, types, defaults, and primary key of a single table.

    Risk level: LOW.
    """
    existing = await list_tables(pool)
    if table_name not in existing["tables"]:
        raise ValueError(f"Table '{table_name}' does not exist in the public schema.")

    columns_query = """
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = $1
        ORDER BY ordinal_position;
    """
    pk_query = """
        SELECT kcu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
        WHERE tc.constraint_type = 'PRIMARY KEY'
          AND tc.table_name = $1;
    """
    async with pool.acquire() as conn:
        columns = await conn.fetch(columns_query, table_name)
        pks = await conn.fetch(pk_query, table_name)

    pk_names = {r["column_name"] for r in pks}
    return {
        "table": table_name,
        "columns": [
            {
                "name": c["column_name"],
                "type": c["data_type"],
                "nullable": c["is_nullable"] == "YES",
                "default": c["column_default"],
                "primary_key": c["column_name"] in pk_names,
            }
            for c in columns
        ],
    }
