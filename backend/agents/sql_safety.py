"""Conservative SQL checks shared by planner and executor boundaries."""
from __future__ import annotations

import re

_FORBIDDEN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|GRANT|REVOKE|CREATE|MERGE|CALL|COPY)\b",
    re.IGNORECASE,
)
_SQL_FENCE = re.compile(r"```(?:sql)?\s*(.*?)\s*```", re.IGNORECASE | re.DOTALL)
_SQL_LABEL = re.compile(r"(?:^|\b)(?:sql|query)\s*:\s*((?:SELECT|WITH)\b.*)$", re.IGNORECASE | re.DOTALL)


def normalize_read_only_sql(sql: str) -> str:
    """Return normalized SQL or reject anything not clearly single/read-only."""
    if not isinstance(sql, str):
        raise ValueError("database.query requires a string SQL statement")
    statement = sql.strip()
    if statement.endswith(";"):
        statement = statement[:-1].rstrip()
    if not statement:
        raise ValueError("database.query requires a non-empty SQL statement")
    if ";" in statement:
        raise ValueError("database.query accepts only one SQL statement")
    if "--" in statement or "/*" in statement or "*/" in statement:
        raise ValueError("SQL comments are not accepted by database.query")
    if not re.match(r"^(SELECT|WITH)\b", statement, flags=re.IGNORECASE):
        raise ValueError("database.query accepts only read-only SELECT or WITH statements")
    if _FORBIDDEN.search(statement):
        raise ValueError("database.query rejected a write or DDL keyword")
    return statement


def extract_explicit_read_only_sql(user_request: str) -> str | None:
    """Extract SQL only when the user supplied an explicit SQL-shaped value."""
    stripped = user_request.strip()
    candidates: list[str] = []
    fence = _SQL_FENCE.search(stripped)
    if fence:
        candidates.append(fence.group(1))
    label = _SQL_LABEL.search(stripped)
    if label:
        candidates.append(label.group(1))
    if re.match(r"^(SELECT|WITH)\b", stripped, flags=re.IGNORECASE):
        candidates.append(stripped)

    for candidate in candidates:
        try:
            return normalize_read_only_sql(candidate)
        except ValueError:
            continue
    return None
