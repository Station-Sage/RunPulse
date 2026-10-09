"""스키마 v31 plan_adjustments: 멱등, CHECK, 부분 유니크."""
import sqlite3

import pytest

from src.db_schema_v31 import ensure_v31
from src.db_setup import APP_TABLES, SCHEMA_VERSION, create_tables, migrate_db

_INS = ("INSERT INTO plan_adjustments(workout_id,date,source,before_json,after_json,rule_version,decision)"
        " VALUES (?,?,?,?,?,?,?)")


def _row(conn, decision="proposed", source="crs", wid=1):
    conn.execute(_INS, (wid, "2026-10-08", source, "{}", "{}", "adjuster_v1", decision))


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    ensure_v31(c)
    return c


def test_idempotent():
    c = sqlite3.connect(":memory:")
    ensure_v31(c)
    ensure_v31(c)
    assert c.execute("SELECT count(*) FROM plan_adjustments").fetchone()[0] == 0


def test_check_constraints(conn):
    with pytest.raises(sqlite3.IntegrityError):
        _row(conn, source="bogus")
    with pytest.raises(sqlite3.IntegrityError):
        _row(conn, decision="bogus")


def test_partial_unique_live(conn):
    _row(conn)
    with pytest.raises(sqlite3.IntegrityError):
        _row(conn, decision="accepted")
    _row(conn, source="user")  # 다른 출처는 허용
    conn.execute("UPDATE plan_adjustments SET decision='reverted' WHERE source='crs'")
    _row(conn)  # reverted 후 새 행 허용


def test_registered_in_create_tables(tmp_path):
    c = sqlite3.connect(tmp_path / "t.db")
    create_tables(c)
    c.execute("PRAGMA user_version = 30")
    migrate_db(c)
    assert "plan_adjustments" in APP_TABLES
    assert c.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION >= 31
    assert c.execute("SELECT name FROM sqlite_master WHERE name='ux_plan_adj_live'").fetchone()
