"""스키마 v42 (신발 관리 v2: user_shoes·activity_shoe·gear.shoe_id) 테스트."""
import sqlite3

import pytest

from src.db_schema_v42 import ensure_v42
from src.db_setup import SCHEMA_VERSION, create_tables


def _cols(c, t):
    return {r[1] for r in c.execute(f"PRAGMA table_info({t})")}


def _v41_gear(c):
    c.execute("CREATE TABLE gear (id INTEGER PRIMARY KEY, source TEXT NOT NULL, source_gear_id TEXT NOT NULL,"
              " name TEXT, UNIQUE(source, source_gear_id))")
    c.execute("INSERT INTO gear (source, source_gear_id, name) VALUES ('strava','g1','A')")


def test_v41_to_v42_idempotent_keeps_gear_rows():
    c = sqlite3.connect(":memory:")
    _v41_gear(c)
    ensure_v42(c)
    ensure_v42(c)
    assert "shoe_id" in _cols(c, "gear")
    assert {"user_shoes", "activity_shoe"} <= {r[0] for r in c.execute("SELECT name FROM sqlite_master")}
    assert c.execute("SELECT name, shoe_id FROM gear").fetchall() == [("A", None)]


def test_new_db_ddl_matches_migrated():
    new = sqlite3.connect(":memory:")
    create_tables(new)
    assert SCHEMA_VERSION == 42
    assert "shoe_id" in _cols(new, "gear")
    old = sqlite3.connect(":memory:")
    _v41_gear(old)
    ensure_v42(old)
    for t in ("user_shoes", "activity_shoe"):
        assert _cols(new, t) == _cols(old, t)


def test_one_active_default_per_kind():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    c.execute("INSERT INTO user_shoes (name, default_for) VALUES ('a','road')")
    with pytest.raises(sqlite3.IntegrityError):
        c.execute("INSERT INTO user_shoes (name, default_for) VALUES ('b','road')")
    c.execute("INSERT INTO user_shoes (name, default_for, retired_at) VALUES ('c','road','2026-01-01')")
    c.execute("INSERT INTO user_shoes (name, default_for) VALUES ('d','trail')")


def test_shoe_delete_sets_gear_null_with_fk():
    c = sqlite3.connect(":memory:")
    c.execute("PRAGMA foreign_keys=ON")
    create_tables(c)
    c.execute("INSERT INTO user_shoes (id, name) VALUES (1,'a')")
    c.execute("INSERT INTO gear (source, source_gear_id, shoe_id) VALUES ('strava','g1',1)")
    c.execute("INSERT INTO activity_shoe (activity_id, shoe_id) VALUES (10, 1)")
    c.execute("DELETE FROM user_shoes WHERE id=1")
    assert c.execute("SELECT shoe_id FROM gear").fetchone() == (None,)
    assert c.execute("SELECT COUNT(*) FROM gear").fetchone() == (1,)
    assert c.execute("SELECT COUNT(*) FROM activity_shoe").fetchone() == (0,)


def test_check_constraints():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    for bad in ("category", "retire_km", "initial_distance_m"):
        val = {"category": "'x'", "retire_km": "50", "initial_distance_m": "-1"}[bad]
        with pytest.raises(sqlite3.IntegrityError):
            c.execute(f"INSERT INTO user_shoes (name, {bad}) VALUES ('a', {val})")
