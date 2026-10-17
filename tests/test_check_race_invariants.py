"""RC-e: 대회 불변식 3·4 검사."""
import sqlite3

import pytest

from scripts.check_race_invariants import check_race_invariants
from src.db_setup import create_tables, migrate_db


@pytest.fixture
def db(tmp_path):
    f = tmp_path / "running.db"
    c = sqlite3.connect(str(f))
    create_tables(c)
    migrate_db(c)
    c.commit()
    c.close()
    return f


def _run(f, sql, *a):
    c = sqlite3.connect(str(f))
    c.execute(sql, a)
    c.commit()
    c.close()


def _race(f, priority="A", status="planned", gtype="time", gval=12000):
    _run(f, "INSERT INTO race_calendar(name, race_date, distance_km, priority, status, goal_type, goal_value)"
            " VALUES ('r', '2099-12-06', 21.1, ?, ?, ?, ?)", priority, status, gtype, gval)


def _goal(f, status="active", race_date="2099-12-06", tt=12000, dist=21.1):
    _run(f, "INSERT INTO goals(name, distance_km, race_date, target_time_sec, status, race_id) VALUES ('g', ?, ?, ?, ?, 1)",
         dist, race_date, tt, status)


def _levels(f):
    return [lv for lv, _ in check_race_invariants(str(f))]


def test_clean_and_empty(db):
    assert _levels(db) == ["✅", "✅"]
    _race(db)
    _goal(db)
    assert _levels(db) == ["✅", "✅"]


def test_invariant3_violation(db):
    _race(db, priority="B")
    _goal(db)
    assert _levels(db)[0] == "🔴"


def test_invariant4_cache_mismatch(db):
    _race(db)
    _goal(db, tt=9999)
    assert _levels(db) == ["✅", "🔴"]


def test_finish_race_expects_null_target(db):
    _race(db, gtype="finish", gval=None)
    _goal(db, tt=None)
    assert _levels(db) == ["✅", "✅"]


def test_inactive_null_date_exception(db):
    _race(db)
    _goal(db, status="completed", race_date=None)
    assert _levels(db) == ["✅", "✅"]
