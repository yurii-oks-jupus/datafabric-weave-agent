"""12 analytics tools exposed to the ADK LLM as plain Python callables.

Each function's docstring is the tool description the LLM sees; keep it
concrete and finance-specific. The underlying SQL/engine code lives in
`core.db`.

Grouping (for sub-agent tool filters):
  schema:  list_tables, describe_table, missing_value_analysis, sample_data
  stats:   summary_statistics, histogram, correlation_matrix
  segment: value_counts, group_by_aggregation
  fraud:   detect_outliers, time_series_aggregation, run_custom_query
"""

from __future__ import annotations

from typing import Any

from core.db import (
    MAX_ROWS,
    _safe,
    _sanitise,
    check_select_only,
    enforce_limit,
    execute_query,
    execute_scalar,
    numeric_columns,
    percentiles,
)

# ---------------------------------------------------------------------------
# Schema tools
# ---------------------------------------------------------------------------


def list_tables() -> dict:
    """List all tables in the public schema.

    Call this first to discover what data is available before any analysis.
    """
    rows = execute_query(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'public' ORDER BY table_name"
    )
    return {"tables": [r["table_name"] for r in rows], "db_type": "postgresql"}


def describe_table(table_name: str) -> dict:
    """Describe a table's columns, types, null counts and total row count.

    Run this before any analysis to understand available columns.
    """
    t = _sanitise(table_name)
    row_count = execute_scalar(f'SELECT COUNT(*) AS c FROM "{t}"')

    col_rows = execute_query(
        """
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = :table_name AND table_schema = 'public'
        ORDER BY ordinal_position
        """,
        {"table_name": t},
    )

    columns: list[dict] = []
    for col in col_rows:
        cname = col["column_name"]
        null_count = execute_scalar(f'SELECT COUNT(*) FROM "{t}" WHERE "{cname}" IS NULL')
        columns.append(
            {
                "name": cname,
                "type": col["data_type"],
                "nullable": col["is_nullable"] == "YES",
                "null_count": null_count,
            }
        )

    return {"table": t, "row_count": row_count, "columns": columns}


def missing_value_analysis(table_name: str) -> dict:
    """Audit every column for null/missing values, sorted most-missing first.

    Essential before ML feature engineering — identifies which columns need
    imputation or removal.
    """
    info = describe_table(table_name)
    total = info["row_count"]
    cols: list[dict] = []
    for col in info["columns"]:
        nc = col["null_count"]
        cols.append(
            {
                "column": col["name"],
                "null_count": nc,
                "null_pct": round(nc / total * 100, 4) if total else 0,
                "complete_pct": round((total - nc) / total * 100, 4) if total else 0,
            }
        )
    cols.sort(key=lambda x: x["null_pct"], reverse=True)
    return {"table": info["table"], "total_rows": total, "columns": cols}


def sample_data(table_name: str, n: int = 10, method: str = "first") -> dict:
    """Preview a sample of rows from a table.

    Args:
        table_name: Target table.
        n: Number of rows to return (1-500).
        method: 'first' | 'last' | 'random'. Use 'random' to avoid always
                seeing the same date range.
    """
    if method not in ("first", "last", "random"):
        raise ValueError(f"method must be one of first|last|random, got {method!r}")
    if not 1 <= n <= MAX_ROWS:
        raise ValueError(f"n must be between 1 and {MAX_ROWS}")

    t = _sanitise(table_name)
    if method == "random":
        sql = f'SELECT * FROM "{t}" ORDER BY RANDOM() LIMIT {n}'
    elif method == "last":
        sql = f'SELECT * FROM "{t}" ORDER BY ctid DESC LIMIT {n}'
    else:
        sql = f'SELECT * FROM "{t}" LIMIT {n}'

    rows = execute_query(sql)
    return {"table": t, "sample_method": method, "row_count": len(rows), "rows": rows}


# ---------------------------------------------------------------------------
# Stats tools
# ---------------------------------------------------------------------------


def summary_statistics(table_name: str, columns: list[str] | None = None) -> dict:
    """Descriptive statistics (count, mean, std, min/p25/median/p75/max, nulls).

    Omit `columns` to auto-select all numeric fields. On the finance dataset,
    the huge gap between p75 (~£400) and max (~£9,800) on 'amount' is the
    primary fraud signal.
    """
    t = _sanitise(table_name)
    cols = columns or numeric_columns(t)
    if not cols:
        return {"table": t, "statistics": {}, "note": "No numeric columns found."}

    stats: dict[str, dict] = {}
    for col in cols:
        c = _sanitise(col)
        row = execute_query(
            f"""
            SELECT
                COUNT("{c}")            AS cnt,
                AVG("{c}")              AS mean,
                STDDEV("{c}")           AS std,
                MIN("{c}")              AS min_val,
                MAX("{c}")              AS max_val,
                COUNT(*) - COUNT("{c}") AS null_count
            FROM "{t}"
            """
        )[0]
        pct = percentiles(t, c)
        stats[col] = {
            "count": row["cnt"],
            "mean": _safe(row["mean"]),
            "std": _safe(row["std"]),
            "min": _safe(row["min_val"]),
            "max": _safe(row["max_val"]),
            "null_count": row["null_count"],
            **pct,
        }
    return {"table": t, "statistics": stats}


def histogram(table_name: str, column: str, bins: int = 10) -> dict:
    """Equal-width histogram for a numeric column.

    Returns bin edges, counts, and percentages. On 'amount' the distribution
    is bimodal — cluster at £10-£600 (legitimate), thin tail at £2k+ (fraud).
    """
    if not 2 <= bins <= 100:
        raise ValueError(f"bins must be between 2 and 100, got {bins}")

    t = _sanitise(table_name)
    c = _sanitise(column)

    row = execute_query(f'SELECT MIN("{c}") AS lo, MAX("{c}") AS hi FROM "{t}"')[0]
    min_val = float(row["lo"] or 0)
    max_val = float(row["hi"] or 0)

    if min_val == max_val:
        cnt = execute_scalar(f'SELECT COUNT(*) FROM "{t}"')
        return {
            "table": t,
            "column": column,
            "bins": [{"bin_start": min_val, "bin_end": max_val, "count": cnt, "pct": 100.0}],
        }

    bw = (max_val - min_val) / bins
    total = execute_scalar(f'SELECT COUNT(*) FROM "{t}" WHERE "{c}" IS NOT NULL')

    cases: list[str] = []
    for i in range(bins):
        lo = min_val + i * bw
        hi = lo + bw
        op = "<=" if i == bins - 1 else "<"
        cases.append(f'WHEN "{c}" >= {lo} AND "{c}" {op} {hi} THEN {i}')

    sql = (
        f"SELECT CASE {' '.join(cases)} END AS bin_idx, COUNT(*) AS cnt "
        f'FROM "{t}" WHERE "{c}" IS NOT NULL GROUP BY bin_idx ORDER BY bin_idx'
    )
    rows = execute_query(sql)
    row_map = {r["bin_idx"]: r["cnt"] for r in rows if r["bin_idx"] is not None}

    bins_out: list[dict] = []
    for i in range(bins):
        lo = round(min_val + i * bw, 6)
        hi = round(lo + bw, 6)
        cnt_i = row_map.get(i, 0)
        bins_out.append(
            {
                "bin_start": lo,
                "bin_end": hi,
                "count": cnt_i,
                "pct": round(cnt_i / total * 100, 2) if total else 0,
            }
        )

    return {"table": t, "column": column, "bins": bins_out}


def correlation_matrix(table_name: str, columns: list[str] | None = None) -> dict:
    """Pearson correlation between numeric columns (-1 to +1).

    On the finance dataset, correlation between 'amount' and 'is_fraud' is
    the core modelling insight (expected ~0.65+).
    """
    t = _sanitise(table_name)
    cols = columns or numeric_columns(t)[:10]
    if len(cols) < 2:
        return {
            "table": t,
            "columns": cols,
            "matrix": {},
            "note": "Need at least 2 numeric columns.",
        }

    matrix: dict[str, dict] = {}
    for c1 in cols:
        matrix[c1] = {}
        for c2 in cols:
            if c1 == c2:
                matrix[c1][c2] = 1.0
                continue
            rows = execute_query(
                f'SELECT CORR("{_sanitise(c1)}", "{_sanitise(c2)}") AS corr '
                f'FROM "{t}" '
                f'WHERE "{_sanitise(c1)}" IS NOT NULL '
                f'  AND "{_sanitise(c2)}" IS NOT NULL'
            )
            matrix[c1][c2] = _safe(rows[0]["corr"]) if rows else None

    return {"table": t, "columns": cols, "matrix": matrix}


# ---------------------------------------------------------------------------
# Segment tools
# ---------------------------------------------------------------------------


def value_counts(table_name: str, column: str, top_n: int = 20) -> dict:
    """Count of each unique value in a column, sorted descending.

    Best for categorical columns: category, region, channel, is_fraud.
    """
    if not 1 <= top_n <= 200:
        raise ValueError(f"top_n must be between 1 and 200, got {top_n}")

    t = _sanitise(table_name)
    c = _sanitise(column)

    total = execute_scalar(f'SELECT COUNT(*) FROM "{t}"')
    distinct = execute_scalar(f'SELECT COUNT(DISTINCT "{c}") FROM "{t}"')

    rows = execute_query(
        f'SELECT "{c}" AS value, COUNT(*) AS cnt FROM "{t}" '
        f'GROUP BY "{c}" ORDER BY cnt DESC LIMIT {top_n}'
    )
    counts = [
        {
            "value": r["value"],
            "count": r["cnt"],
            "pct": round(r["cnt"] / total * 100, 2) if total else 0,
        }
        for r in rows
    ]
    return {
        "table": t,
        "column": column,
        "total_rows": total,
        "distinct_count": distinct,
        "top_n": top_n,
        "counts": counts,
    }


def group_by_aggregation(
    table_name: str,
    group_by_columns: list[str],
    agg_column: str,
    agg_function: str = "SUM",
    order_by: str = "desc",
    limit: int = 50,
) -> dict:
    """Flexible GROUP BY: SUM/AVG/COUNT/MIN/MAX/COUNT_DISTINCT.

    Use for: revenue by region, fraud count by channel, avg amount by category.
    """
    allowed_fns = {"SUM", "AVG", "COUNT", "MIN", "MAX", "COUNT_DISTINCT"}
    if agg_function not in allowed_fns:
        raise ValueError(f"agg_function must be one of {sorted(allowed_fns)}")
    if order_by not in ("asc", "desc"):
        raise ValueError(f"order_by must be asc|desc, got {order_by!r}")
    if not 1 <= limit <= MAX_ROWS:
        raise ValueError(f"limit must be between 1 and {MAX_ROWS}")

    t = _sanitise(table_name)
    group_cols = [_sanitise(c) for c in group_by_columns]
    order_dir = order_by.upper()
    group_sql = ", ".join(f'"{c}"' for c in group_cols)

    if agg_function == "COUNT_DISTINCT":
        agg_col = _sanitise(agg_column)
        agg_expr = f'COUNT(DISTINCT "{agg_col}")'
        agg_label = f"COUNT_DISTINCT({agg_column})"
    elif agg_function == "COUNT" and agg_column == "*":
        agg_expr = "COUNT(*)"
        agg_label = "COUNT(*)"
    else:
        agg_col = _sanitise(agg_column)
        agg_expr = f'{agg_function}("{agg_col}")'
        agg_label = f"{agg_function}({agg_column})"

    sql = (
        f"SELECT {group_sql}, {agg_expr} AS agg_value "
        f'FROM "{t}" GROUP BY {group_sql} '
        f"ORDER BY agg_value {order_dir} LIMIT {limit}"
    )
    rows = execute_query(sql)
    return {
        "table": t,
        "group_by": group_by_columns,
        "aggregation": agg_label,
        "row_count": len(rows),
        "rows": rows,
    }


# ---------------------------------------------------------------------------
# Fraud tools
# ---------------------------------------------------------------------------


def detect_outliers(table_name: str, column: str, method: str = "iqr") -> dict:
    """Identify statistical outliers via IQR (1.5×IQR rule) or Z-score (±3σ).

    On the finance dataset, nearly all is_fraud=1 rows surface as 'amount'
    outliers. Returns bounds, outlier count, percentage, and a sample.
    """
    if method not in ("iqr", "zscore"):
        raise ValueError(f"method must be iqr|zscore, got {method!r}")

    t = _sanitise(table_name)
    c = _sanitise(column)

    if method == "zscore":
        rows = execute_query(
            f'SELECT AVG("{c}") AS mean, STDDEV("{c}") AS std FROM "{t}" WHERE "{c}" IS NOT NULL'
        )
        mean = float(rows[0]["mean"] or 0)
        std = float(rows[0]["std"] or 0)
        if std == 0:
            return {
                "table": t,
                "column": column,
                "method": "zscore",
                "outlier_count": 0,
                "note": "Zero variance.",
            }
        lower = mean - 3 * std
        upper = mean + 3 * std
        extra: dict[str, Any] = {"mean": round(mean, 4), "std": round(std, 4)}
    else:
        pct = percentiles(t, c)
        q1, q3 = pct["p25"], pct["p75"]
        if q1 is None or q3 is None:
            return {
                "table": t,
                "column": column,
                "method": "iqr",
                "note": "Could not compute quartiles.",
            }
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        extra = {"q1": q1, "q3": q3, "iqr": round(iqr, 4)}

    outlier_count = execute_scalar(
        f'SELECT COUNT(*) FROM "{t}" WHERE "{c}" < {lower} OR "{c}" > {upper}'
    )
    total = execute_scalar(f'SELECT COUNT(*) FROM "{t}" WHERE "{c}" IS NOT NULL')
    sample = execute_query(f'SELECT * FROM "{t}" WHERE "{c}" < {lower} OR "{c}" > {upper} LIMIT 10')

    return {
        "table": t,
        "column": column,
        "method": method,
        "bounds": {"lower": round(lower, 4), "upper": round(upper, 4)},
        "outlier_count": outlier_count,
        "outlier_pct": round(outlier_count / total * 100, 4) if total else 0,
        "sample_outliers": sample,
        **extra,
    }


def time_series_aggregation(
    table_name: str,
    date_column: str,
    value_column: str,
    granularity: str = "month",
    agg_function: str = "SUM",
) -> dict:
    """Aggregate a numeric metric at day/week/month/quarter/year granularity.

    Use for monthly spend trends, weekly fraud counts, quarterly revenue.
    """
    if granularity not in ("day", "week", "month", "quarter", "year"):
        raise ValueError(f"granularity unsupported: {granularity!r}")
    if agg_function not in ("SUM", "AVG", "COUNT", "MIN", "MAX"):
        raise ValueError(f"agg_function unsupported: {agg_function!r}")

    t = _sanitise(table_name)
    dc = _sanitise(date_column)
    vc = _sanitise(value_column)

    sql = (
        f"SELECT DATE_TRUNC('{granularity}', \"{dc}\") AS period, "
        f'{agg_function}("{vc}") AS value '
        f'FROM "{t}" WHERE "{dc}" IS NOT NULL AND "{vc}" IS NOT NULL '
        f"GROUP BY period ORDER BY period"
    )
    rows = execute_query(sql)
    series = [{"period": str(r["period"])[:10], "value": _safe(r["value"])} for r in rows]

    return {
        "table": t,
        "date_column": date_column,
        "value_column": value_column,
        "granularity": granularity,
        "aggregation": agg_function,
        "series": series,
    }


def run_custom_query(sql: str, max_rows: int = 200) -> dict:
    """Execute a read-only SQL SELECT (or WITH...SELECT CTE).

    Results capped at max_rows (hard cap 500). Only SELECT and WITH are
    accepted; INSERT/UPDATE/DELETE/DDL keywords anywhere in the query are
    rejected. Use for bespoke investigations: customers with mixed fraud+legit
    records, category × channel cross-tabs, rolling averages.
    """
    if not 1 <= max_rows <= MAX_ROWS:
        raise ValueError(f"max_rows must be between 1 and {MAX_ROWS}")

    sql = sql.strip()
    check_select_only(sql)
    cap = min(max_rows, MAX_ROWS)
    sql = enforce_limit(sql, cap)

    rows = execute_query(sql)[:cap]
    return {
        "columns": list(rows[0].keys()) if rows else [],
        "rows": rows,
        "row_count": len(rows),
        "truncated": len(rows) >= cap,
    }


# ---------------------------------------------------------------------------
# Tool groupings used by sub-agents
# ---------------------------------------------------------------------------

SCHEMA_TOOLS = [list_tables, describe_table, missing_value_analysis, sample_data]
STATS_TOOLS = [summary_statistics, histogram, correlation_matrix]
SEGMENT_TOOLS = [value_counts, group_by_aggregation]
FRAUD_TOOLS = [detect_outliers, time_series_aggregation, run_custom_query]
