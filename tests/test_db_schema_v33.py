"""스키마 v33 plan_replans.start_source 확장: 멱등, 행·인덱스 보존, 새 값 허용."""
import sqlite3

import pytest

from src.db_schema_v32 import ensure_v32
from src.db_schema_v33 import ensure_v33
from src.db_setup import SCHEMA_VERSION


def _v32_conn():
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE goals (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, status TEXT NOT NULL DEFAULT 'active',"
              " created_at TEXT NOT NULL DEFAULT (datetime('now')))")
    ensure_v32(c)
    return c


def test_preserves_rows_and_index_and_idempotent():
    c = _v32_conn()
    c.execute("INSERT INTO plan_replans(goal_id,anchor_monday,start_km,start_source,status) VALUES (1,'2026-10-12',30,'history','undone')")
    ensure_v33(c)
    ensure_v33(c)
    assert c.execute("SELECT id,start_km,start_source,status FROM plan_replans").fetchall() == [(1, 30.0, "history", "undone")]
    assert c.execute("SELECT 1 FROM sqlite_master WHERE name='idx_plan_replans_goal'").fetchone()
    assert c.execute("SELECT name FROM sqlite_master WHERE name='plan_replans_new'").fetchone() is None


def test_new_sources_allowed_bogus_rejected():
    c = _v32_conn()
    ensure_v33(c)
    for s in ("user", "history", "floor", "avg16", "default"):
        c.execute("INSERT INTO plan_replans(goal_id,anchor_monday,start_km,start_source) VALUES (1,'2026-10-12',30,?)", (s,))
    with pytest.raises(sqlite3.IntegrityError):
        c.execute("INSERT INTO plan_replans(goal_id,anchor_monday,start_km,start_source) VALUES (1,'2026-10-12',30,'bogus')")


def test_schema_version():
    assert SCHEMA_VERSION >= 33
