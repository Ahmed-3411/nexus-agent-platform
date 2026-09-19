"""
Unit tests for the PostgreSQL MCP server's read-only enforcement and
tool logic.

Requires: pip install -r mcp/postgres/requirements.txt pytest pytest-asyncio

Run from the repo root:
    pytest tests/unit/test_postgres_mcp_tools.py -v
"""
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

import importlib.util

_TOOLS_PATH = Path(__file__).resolve().parents[2] / "mcp/postgres/tools.py"
_SPEC = importlib.util.spec_from_file_location("_test_pg_tools_module", _TOOLS_PATH)
assert _SPEC is not None and _SPEC.loader is not None
pg_tools = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(pg_tools)


class TestAssertReadOnly:
    @pytest.mark.parametrize(
        "sql",
        [
            "SELECT * FROM customers",
            "select id, name from customers where id = 1",
            "WITH recent AS (SELECT * FROM orders) SELECT * FROM recent",
            "  SELECT 1;  ",
        ],
    )
    def test_allows_select_statements(self, sql):
        pg_tools._assert_read_only(sql)  # should not raise

    @pytest.mark.parametrize(
        "sql",
        [
            "DELETE FROM customers",
            "UPDATE customers SET name = 'x'",
            "DROP TABLE customers",
            "INSERT INTO customers VALUES (1, 'x')",
            "TRUNCATE customers",
            "ALTER TABLE customers ADD COLUMN x INT",
            "SELECT * FROM customers; DROP TABLE customers;",
        ],
    )
    def test_rejects_write_and_multi_statements(self, sql):
        with pytest.raises((pg_tools.NotReadOnlyError, ValueError)):
            pg_tools._assert_read_only(sql)

    def test_rejects_empty_statement(self):
        with pytest.raises(ValueError):
            pg_tools._assert_read_only("   ")


def _make_fake_pool(fetch_results):
    """
    Build a fake asyncpg pool whose `acquire()` context manager returns a
    connection whose `fetch()` yields the given results (a list, or a
    callable taking (query, *args) for multi-call scenarios).
    """
    conn = MagicMock()

    async def fetch(query, *args):
        if callable(fetch_results):
            return fetch_results(query, *args)
        return fetch_results

    conn.fetch = AsyncMock(side_effect=fetch)

    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
    return pool


class TestQueryDatabase:
    @pytest.mark.asyncio
    async def test_returns_rows_and_row_count(self):
        rows = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
        pool = _make_fake_pool(rows)

        result = await pg_tools.query_database(pool, "SELECT * FROM customers")

        assert result["row_count"] == 2
        assert result["truncated"] is False
        assert result["rows"] == rows

    @pytest.mark.asyncio
    async def test_truncates_beyond_row_limit(self):
        rows = [{"id": i} for i in range(10)]
        pool = _make_fake_pool(rows)

        result = await pg_tools.query_database(pool, "SELECT * FROM customers", row_limit=3)

        assert result["row_count"] == 3
        assert result["truncated"] is True

    @pytest.mark.asyncio
    async def test_blocks_write_query_before_hitting_db(self):
        pool = _make_fake_pool([])
        with pytest.raises(pg_tools.NotReadOnlyError):
            await pg_tools.query_database(pool, "DELETE FROM customers")
        pool.acquire.assert_not_called()


class TestListTables:
    @pytest.mark.asyncio
    async def test_lists_table_names(self):
        rows = [{"table_name": "customers"}, {"table_name": "orders"}]
        pool = _make_fake_pool(rows)

        result = await pg_tools.list_tables(pool)

        assert result["tables"] == ["customers", "orders"]


class TestDescribeTable:
    @pytest.mark.asyncio
    async def test_raises_for_unknown_table(self):
        pool = _make_fake_pool([])  # list_tables() returns no tables
        with pytest.raises(ValueError, match="does not exist"):
            await pg_tools.describe_table(pool, "ghost_table")

    @pytest.mark.asyncio
    async def test_describes_known_table_with_primary_key(self):
        def fetch_side_effect(query, *args):
            if "information_schema.tables" in query:
                return [{"table_name": "customers"}]
            if "table_constraints" in query:
                return [{"column_name": "id"}]
            # column listing query
            return [
                {
                    "column_name": "id",
                    "data_type": "uuid",
                    "is_nullable": "NO",
                    "column_default": None,
                },
                {
                    "column_name": "name",
                    "data_type": "text",
                    "is_nullable": "YES",
                    "column_default": None,
                },
            ]

        pool = _make_fake_pool(fetch_side_effect)

        result = await pg_tools.describe_table(pool, "customers")

        assert result["table"] == "customers"
        id_col = next(c for c in result["columns"] if c["name"] == "id")
        assert id_col["primary_key"] is True
        name_col = next(c for c in result["columns"] if c["name"] == "name")
        assert name_col["primary_key"] is False
