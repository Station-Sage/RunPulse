"""스키마 v38 — race_calendar·context_episodes·illness_consent_events 가산 CREATE."""
import sqlite3

import pytest

from src.db_schema_v38 import TABLES, dry_run, ensure_v38


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE planned_workouts (id INTEGER PRIMARY KEY)")
    c.execute("CREATE TABLE race_results (id INTEGER PRIMARY KEY)")
    return c


def _race(c, **kw):
    v = dict(name="R", race_date="2026-11-01", distance_km=42.195, priority="B")
    v.update(kw)
    c.execute(f"INSERT INTO race_calendar ({','.join(v)}) VALUES ({','.join('?' * len(v))})", tuple(v.values()))


def test_creates_and_idempotent(conn):
    assert dry_run(conn) == list(TABLES)
    ensure_v38(conn)
    ensure_v38(conn)
    assert dry_run(conn) == []


def test_race_defaults_and_checks(conn):
    ensure_v38(conn)
    _race(conn)
    row = conn.execute("SELECT adapt_choice, plan_state, status, origin, cancel_prev_plan_state FROM race_calendar").fetchone()
    assert row == ("unasked", "none", "planned", "manual", None)
    for bad in ({"priority": "D"}, {"priority": None}, {"goal_type": "x"}, {"status": "x"},
                {"cancel_prev_adapt_choice": "x"}, {"cancel_prev_plan_state": "x"}, {"origin": "x"}):
        with pytest.raises(sqlite3.IntegrityError):
            _race(conn, race_date="2027-01-01", **bad)
    _race(conn, race_date="2027-02-01", cancel_prev_adapt_choice="later", cancel_prev_plan_state="applied")


def test_race_unique_indexes(conn):
    ensure_v38(conn)
    _race(conn, priority="A")
    with pytest.raises(sqlite3.IntegrityError):
        _race(conn, priority="B")  # 같은 날짜·거리 planned
    with pytest.raises(sqlite3.IntegrityError):
        _race(conn, race_date="2027-01-01", priority="A")  # planned A 는 하나
    conn.execute("UPDATE race_calendar SET status='cancelled'")
    _race(conn, priority="A")  # 취소 후엔 가능


def test_context_episodes_checks(conn):
    ensure_v38(conn)
    conn.execute("INSERT INTO context_episodes (kind, start_date, origin, status) VALUES ('illness','2026-10-01','auto','candidate')")
    assert conn.execute("SELECT detail_json, end_date FROM context_episodes").fetchone() == ("{}", None)
    for kind, origin, status in (("flu", "user", "confirmed"), ("travel", "x", "confirmed"), ("travel", "user", "x")):
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO context_episodes (kind, start_date, origin, status) VALUES (?,?,?,?)",
                         (kind, "2026-10-01", origin, status))


def test_illness_consent_checks(conn):
    ensure_v38(conn)
    conn.execute("INSERT INTO illness_consent_events (action, via) VALUES ('grant','settings')")
    assert conn.execute("SELECT created_at FROM illness_consent_events").fetchone()[0]
    for a, v in (("x", "settings"), ("grant", "x")):
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO illness_consent_events (action, via) VALUES (?,?)", (a, v))


def test_full_chain_reaches_v38(db_conn):
    assert db_conn.execute("PRAGMA user_version").fetchone()[0] >= 38
    assert dry_run(db_conn) == []


def test_lookup_indexes_exist_and_used(conn):
    ensure_v38(conn)
    names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='index'")}
    assert {"idx_episodes_kind_status", "idx_race_status_date"} <= names
    plan = " ".join(r[3] for r in conn.execute(
        "EXPLAIN QUERY PLAN SELECT * FROM context_episodes WHERE kind='illness' AND status='confirmed'"))
    assert "idx_episodes_kind_status" in plan
