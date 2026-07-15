"""DuckDB connection helpers shared across the pipeline, models, and app layers."""

import os
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
    try:
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = duckdb.connect(db_path)
        logger.success(f"Connected to DuckDB at {db_path}")
        return conn
    except Exception as exc:
        logger.error(f"Failed to connect to DuckDB at {db_path}: {exc}")
        raise


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
) -> any:
    """Execute a SQL query against the given connection.

    Args:
        conn: An open DuckDB connection.
        query: SQL query string to execute.
        params: Optional list of parameters to bind to the query.

    Returns:
        The query result, or None if execution failed.
    """
    try:
        if params is not None:
            return conn.execute(query, params).fetchall()
        return conn.execute(query).fetchall()
    except Exception as exc:
        logger.error(f"Query failed: {query} | error: {exc}")
        return None
