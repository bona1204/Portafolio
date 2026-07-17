"""DuckDB connection helpers shared across the pipeline, models, and app layers."""

from pathlib import Path
from typing import Optional

import duckdb
from loguru import logger


def init_db(db_path: str = "data/portfolio.duckdb") -> duckdb.DuckDBPyConnection:
    """Create (if needed) the parent directory and open a DuckDB connection.

    Args:
        db_path: Filesystem path to the DuckDB database file.

    Returns:
        An open DuckDB connection.
    """
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(db_path)
    logger.success(f"Connected to DuckDB at {db_path}")
    return conn


def get_conn(db_path: str = "data/portfolio.duckdb") -> duckdb.DuckDBPyConnection:
    """Return a DuckDB connection, creating the database if it does not exist.

    Args:
        db_path: Filesystem path to the DuckDB database file.

    Returns:
        An open DuckDB connection.
    """
    return init_db(db_path)


def execute_query(
    conn: duckdb.DuckDBPyConnection,
    query: str,
    params: Optional[list] = None,
) -> list:
    """Execute a SQL query against the given connection.

    Deliberately does not catch query errors: a failed query almost always
    means a real bug (missing table, typo'd column, bad params) that
    callers need to see, not silently swallow into an empty/None result —
    an earlier version of this function caught and logged all exceptions
    here, which made `train.py:load_features` misreport a broken query as
    "mart_player_season returned no rows — run dbt run first" instead of
    surfacing the actual error.

    Args:
        conn: An open DuckDB connection.
        query: SQL query string to execute.
        params: Optional list of parameters to bind to the query.

    Returns:
        The query result as a list of row tuples.
    """
    if params is not None:
        return conn.execute(query, params).fetchall()
    return conn.execute(query).fetchall()
