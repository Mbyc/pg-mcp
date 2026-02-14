import pytest

from pg_mcp.sql.safety import validate_readonly_sql


def test_allows_simple_select():
    res = validate_readonly_sql("SELECT 1")
    assert res.is_readonly


def test_allows_with_select():
    res = validate_readonly_sql("WITH t AS (SELECT 1 AS x) SELECT x FROM t")
    assert res.is_readonly


def test_rejects_multi_statement_by_default():
    res = validate_readonly_sql("SELECT 1; SELECT 2")
    assert not res.is_readonly
    assert "multi_statement_not_allowed" in res.blocked_reasons


def test_rejects_insert_update_delete_ddl_copy_set_call_do():
    cases = [
        "INSERT INTO x VALUES (1)",
        "UPDATE x SET a = 1",
        "DELETE FROM x",
        "CREATE TABLE x(a int)",
        "DROP TABLE x",
        "TRUNCATE TABLE x",
        "COPY x TO '/tmp/x'",
        "SET statement_timeout = 1",
        "CALL foo()",
        "DO $$ BEGIN END $$",
    ]
    for sql in cases:
        res = validate_readonly_sql(sql)
        assert not res.is_readonly


def test_rejects_disallowed_functions_case_and_quotes_and_schema_qualified():
    disallowed = ["pg_sleep"]
    cases = [
        "SELECT pg_sleep(1)",
        "SELECT PG_SLEEP(1)",
        'SELECT "pg_sleep"(1)',
        "SELECT pg_catalog.pg_sleep(1)",
    ]
    for sql in cases:
        res = validate_readonly_sql(sql, disallowed_functions=disallowed)
        assert not res.is_readonly
        # 确保 reason 中包含 pg_sleep，不论是否带有 schema 限定
        assert any("pg_sleep" in r for r in res.blocked_reasons)
