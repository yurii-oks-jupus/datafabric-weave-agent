"""Database access layer for the analytics agent.

Consolidates what was previously spread across `finalytics_api.py` and
`finalytics_mcp.py`: a single SQLAlchemy engine, the `_sanitise` identifier
guard, the `_safe` numeric normaliser, and the SELECT-only / forbidden-
keywords SQL guard. All tool functions in `core/tools.py` go through here.

Driver: pg8000 (D12 forbids psycopg2-binary).
"""

from __future__ import annotations

import logging
import math
import re
from functools import lru_cache
from typing import Any

import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from core.config import settings

logger = logging.getLogger(__name__)

MAX_ROWS: int = 500

_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_$]*$")
# Allow both bare SELECT and CTEs (`WITH x AS (...) SELECT ...`); the
# forbidden-keywords regex still blocks anything that could mutate state.
_READ_PREFIX_RE = re.compile(r"^\s*(SELECT|WITH)\b", re.IGNORECASE)
_FORBIDDEN_KEYWORDS_RE = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE|EXEC|GRANT|REVOKE)\b",
    re.IGNORECASE,
)
_LIMIT_RE = re.compile(r"\bLIMIT\b", re.IGNORECASE)


def _db_url() -> str:
    """Build the Postgres DSN from settings. Password comes from env at runtime."""
    vs = settings.vector_stores
    return (
        f"postgresql+pg8000://{vs.db_iam_user}:{vs.db_iam_pass}"
        f"@{vs.db_host}:{vs.db_port}/{vs.db_name}"
    )


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Return a process-wide SQLAlchemy engine (lazy, cached)."""
    return create_engine(_db_url(), pool_pre_ping=True)


def _sanitise(name: str) -> str:
    """Return `name` if it's a valid SQL identifier; raise otherwise."""
    name = name.strip('"').strip("'")
    if not _IDENT_RE.match(name):
        raise ValueError(f"Invalid identifier: {name!r}")
    return name


def _safe(v: Any) -> Any:
    """Coerce numeric values to JSON-safe floats (None for NaN/Inf)."""
    if v is None:
        return None
    try:
        f = float(v)
        return None if (math.isnan(f) or math.isinf(f)) else round(f, 6)
    except (TypeError, ValueError):
        return v


def execute_query(sql: str, params: dict | None = None) -> list[dict]:
    """Run a query and return all rows as dicts."""
    logger.debug("SQL: %s params=%s", sql, params)
    stmt = sqlalchemy.text(sql)
    with get_engine().connect() as conn:
        result = conn.execute(stmt, params or {})
        return [dict(r) for r in result.mappings().all()]


def execute_scalar(sql: str, params: dict | None = None) -> Any:
    """Run a query and return the first column of the first row."""
    logger.debug("SQL (scalar): %s params=%s", sql, params)
    stmt = sqlalchemy.text(sql)
    with get_engine().connect() as conn:
        result = conn.execute(stmt, params or {})
        row = result.first()
        if row is None:
            return None
        return row[0]


def check_select_only(sql: str) -> None:
    """Raise ValueError if `sql` isn't a read query (SELECT or WITH...SELECT) or
    contains a forbidden DML/DDL keyword."""
    if not _READ_PREFIX_RE.match(sql):
        raise ValueError("Only SELECT and WITH...SELECT queries are permitted.")
    if _FORBIDDEN_KEYWORDS_RE.search(sql):
        raise ValueError("Query contains forbidden keywords.")


def enforce_limit(sql: str, max_rows: int) -> str:
    """Append `LIMIT max_rows` if the query doesn't already declare one."""
    if _LIMIT_RE.search(sql):
        return sql
    if sql.rstrip().endswith(";"):
        return sql.rstrip(";").rstrip() + f" LIMIT {max_rows};"
    return f"{sql} LIMIT {max_rows}"


def numeric_columns(table_name: str) -> list[str]:
    """Return the names of numeric columns in `table_name` (public schema)."""
    t = _sanitise(table_name)
    rows = execute_query(
        """
        SELECT column_name FROM information_schema.columns
        WHERE table_name = :table_name AND table_schema = 'public'
          AND data_type IN (
              'integer','bigint','smallint','numeric','real',
              'double precision','decimal','money'
          )
        ORDER BY ordinal_position
        """,
        {"table_name": t},
    )
    return [r["column_name"] for r in rows]


def percentiles(table_name: str, column: str) -> dict:
    """Return the 25th, 50th and 75th percentile of `column` in `table_name`."""
    t = _sanitise(table_name)
    c = _sanitise(column)
    rows = execute_query(
        f"""
        SELECT
            PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY "{c}") AS p25,
            PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY "{c}") AS median,
            PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY "{c}") AS p75
        FROM "{t}"
        WHERE "{c}" IS NOT NULL
        """
    )
    r = rows[0] if rows else {}
    return {
        "p25": _safe(r.get("p25")),
        "median": _safe(r.get("median")),
        "p75": _safe(r.get("p75")),
    }
