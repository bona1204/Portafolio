"""Unit tests for src/utils/db.py: DuckDB connection and query helpers."""

import duckdb
import pytest

from src.utils.db import execute_query


@pytest.fixture
def conn():
    connection = duckdb.connect(":memory:")
    connection.execute("create table players (id integer, name varchar)")
    connection.execute("insert into players values (1, 'Alice'), (2, 'Bob')")
    yield connection
    connection.close()


def test_execute_query_returns_rows(conn):
    rows = execute_query(conn, "select * from players order by id")
    assert rows == [(1, "Alice"), (2, "Bob")]


def test_execute_query_binds_params(conn):
    rows = execute_query(conn, "select name from players where id = ?", [2])
    assert rows == [("Bob",)]


def test_execute_query_raises_on_invalid_sql_instead_of_swallowing_it(conn):
    # A broken query is a real bug (typo'd table/column) and must surface,
    # not get silently logged-and-swallowed into an empty/None result — see
    # the docstring in src/utils/db.py for the incident this replaced.
    with pytest.raises(duckdb.Error):
        execute_query(conn, "select * from nonexistent_table")
