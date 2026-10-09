"""스키마 v32 plan_replans·ux_goals_one_active: 멱등, 중복 active 정리, 유니크 강제."""
import sqlite3

import pytest

from src.db_schema_v32 import ensure_v32
from src.db_setup import APP_TABLES, SCHEMA_VERSION, create_tables, migrate_db


def _goals_conn():
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE goals (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, status TEXT NOT NULL DEFAULT 'active',"
              " created_at TEXT NOT NULL DEFAULT (datetime('now')))")
    return c


def test_idempotent():
    c = _goals_conn()
    ensure_v32(c)
    ensure_v32(c)
    assert c.execute("SELECT count(*) FROM plan_replans").fetchone()[0] == 0


def test_duplicate_active_cleanup_keeps_newest():
    c = _goals_conn()
    c.execute("INSERT INTO goals(name,created_at) VALUES ('a','2026-01-01 00:00:00')")
    c.execute("INSERT INTO goals(name,created_at) VALUES ('b','2026-02-01 00:00:00')")
    c.execute("INSERT INTO goals(name,created_at,status) VALUES ('c','2026-03-01 00:00:00','completed')")
    ensure_v32(c)
    rows = dict(c.execute("SELECT name,status FROM goals").fetchall())
    assert rows == {"a": "cancelled", "b": "active", "c": "completed"}


def test_second_active_insert_fails():
    c = _goals_conn()
    ensure_v32(c)
    c.execute("INSERT INTO goals(name) VALUES ('a')")
    with pytest.raises(sqlite3.IntegrityError):
        c.execute("INSERT INTO goals(name) VALUES ('b')")
    c.execute("INSERT INTO goals(name,status) VALUES ('c','cancelled')")


def test_check_constraints():
    c = _goals_conn()
    ensure_v32(c)
    with pytest.raises(sqlite3.IntegrityError):
        c.execute("INSERT INTO plan_replans(goal_id,anchor_monday,start_km,start_source) VALUES (1,'2026-10-12',30,'bogus')")


def test_registered_and_migrates(tmp_path):
    c = sqlite3.connect(tmp_path / "t.db")
    create_tables(c)
    c.execute("PRAGMA user_version = 31")
    migrate_db(c)
    assert "plan_replans" in APP_TABLES
    assert c.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION == 32
    assert c.execute("SELECT name FROM sqlite_master WHERE name='ux_goals_one_active'").fetchone()
