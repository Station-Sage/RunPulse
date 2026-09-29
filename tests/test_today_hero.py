"""tests/test_today_hero.py — Today 히어로 state 판정·주간 스트립·게이지(10-today design §2.4·§7.3)."""
from __future__ import annotations

import sqlite3

import pytest

from src.db_setup import create_tables, migrate_db
from src.services import today_hero
from src.services.today_readiness import build_readiness
from src.training.goals import add_goal

DAY = "2026-09-29"  # 화요일 — 주 월(09-28)~일(10-04)


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    migrate_db(c)
    yield c
    c.close()


def _goal(conn, race_date="2026-12-06"):
    gid = add_goal(conn, "테스트 대회", 42.195, race_date=race_date)
    conn.execute("UPDATE goals SET created_at = '2026-09-01 00:00:00' WHERE id = ?", (gid,))


def _plan(conn, d, wtype, km):
    conn.execute("INSERT INTO planned_workouts (date, workout_type, distance_km, source, completed)"
                 " VALUES (?, ?, ?, 'planner', 0)", (d, wtype, km))


def _act(conn, d, km):
    conn.execute(
        "INSERT INTO activity_summaries (source, source_id, name, activity_type, start_time,"
        " distance_m, duration_sec, avg_pace_sec_km) VALUES ('garmin', ?, 'Run', 'running', ?, ?, ?, 360)",
        (f"{d}-{km}", f"{d}T07:00:00", km * 1000, km * 360))
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def _link(conn, d, act_id):
    conn.execute("UPDATE planned_workouts SET matched_activity_id = ? WHERE date = ?", (act_id, d))


def _state(conn, day=DAY):
    week = today_hero.build_week(conn, day)
    return today_hero.build_briefing_state(conn, day, week)


def test_no_goal_is_no_plan(conn):
    assert _state(conn)["state"] == "no_plan"


def test_planned_session_not_run_is_pre(conn):
    _goal(conn)
    _plan(conn, DAY, "easy", 8.0)
    b = _state(conn)
    assert b["state"] == "pre" and b["session"]["title"] == "이지런"
    assert b["session"]["distance_m"] == 8000 and b["verdict"] in ("as_planned", "up", "down")


def test_run_on_planned_day_is_done_with_ratio(conn):
    _goal(conn)
    _plan(conn, DAY, "easy", 8.0)
    _act(conn, DAY, 8.0)
    b = _state(conn)
    assert b["state"] == "done" and b["today_result"]["plan_ratio_pct"] == 100


def test_run_on_rest_day_is_extra(conn):
    _goal(conn)
    _plan(conn, DAY, "rest", None)
    _plan(conn, "2026-09-30", "easy", 6.0)
    _act(conn, DAY, 5.0)
    b = _state(conn)
    assert b["state"] == "extra" and b["today_result"]["plan_ratio_pct"] is None


def test_rest_day_without_run(conn):
    _goal(conn)
    _plan(conn, DAY, "rest", None)
    assert _state(conn)["state"] == "rest"


def test_race_week_and_race_day_take_precedence(conn):
    _goal(conn, race_date="2026-10-04")
    _plan(conn, DAY, "easy", 5.0)
    assert _state(conn)["state"] == "race_week"
    assert _state(conn, "2026-10-04")["state"] == "race_day"


def test_week_summary_km_and_key_sessions(conn):
    _goal(conn)
    _plan(conn, "2026-09-28", "easy", 8.0)
    _plan(conn, DAY, "interval", 10.0)
    _plan(conn, "2026-10-03", "long", 20.0)
    _act(conn, "2026-09-28", 8.0)
    _link(conn, DAY, _act(conn, DAY, 10.0))
    w = today_hero.build_week(conn, DAY)
    assert len(w["days"]) == 7
    assert w["plan_km"] == 38.0 and w["done_km"] == 18.0
    assert (w["key_done"], w["key_total"]) == (1, 2)
    assert [d["today"] for d in w["days"]].count(True) == 1


def test_readiness_delta_and_missing(conn):
    conn.execute("INSERT INTO metric_store (scope_type, scope_id, metric_name, numeric_value, provider,"
                 " is_primary) VALUES ('daily', ?, 'utrs', 70, 'runpulse', 1)", (DAY,))
    conn.execute("INSERT INTO metric_store (scope_type, scope_id, metric_name, numeric_value, provider,"
                 " is_primary) VALUES ('daily', '2026-09-28', 'utrs', 64, 'runpulse', 1)")
    r = build_readiness(conn, DAY)
    assert r["utrs"]["value"] == 70 and r["utrs"]["delta_1d"] == 6.0
    assert r["utrs"]["status_label"] and r["cirs"] is None and r["tsb"] is None
