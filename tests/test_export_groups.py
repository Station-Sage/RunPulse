"""export_groups — 허용목록이 실제 스키마를 빠짐없이 덮고, 비밀 컬럼/값을 막는다."""
from __future__ import annotations

import sqlite3

import pytest

from src.db_setup import create_tables, migrate_db
from src.services import export_groups as eg


@pytest.fixture(scope="module")
def real_conn():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    migrate_db(c)
    yield c
    c.close()


def test_every_real_table_is_grouped_or_excluded(real_conn):
    names = {r[0] for r in real_conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
    covered = set(eg.all_group_tables()) | set(eg.ALWAYS_EXCLUDED)
    assert not (names - covered - {"schema_version", "schema_migrations"}), names - covered


def test_no_secret_columns_in_exported_tables(real_conn):
    for t in eg.all_group_tables():
        if eg.table_exists(real_conn, t):
            assert eg.safe_columns(real_conn, t)


def test_secret_column_rejected():
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE t (a TEXT, api_key TEXT)")
    with pytest.raises(ValueError):
        eg.safe_columns(c, "t")


def test_secret_value_detected():
    assert eg.has_secret_value(("x", "enc:abc"))
    assert not eg.has_secret_value(("x", 1, None))


def test_defaults_and_sensitive():
    assert set(eg.DEFAULT_GROUPS) == {"activities", "metrics", "raw", "episodes", "races"}
    assert {"episodes", "coach", "profile"} == set(eg.SENSITIVE_GROUPS)
    assert eg.LEGACY_GROUPS == ("activities", "metrics", "raw")
    assert not set(eg.ALWAYS_EXCLUDED) & set(eg.all_group_tables())
