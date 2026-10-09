"""tests/test_week_compliance.py — 날짜별 유효 계획·이행 수치(31-coach-plan design R1·R2·R3·R5)."""
from __future__ import annotations

import sqlite3
from datetime import date

import pytest

from src.db_setup import create_tables, migrate_db
from src.training import week_compliance as wc

MON = date(2026, 9, 21)
TODAY = date(2026, 9, 28)


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    migrate_db(c)
    yield c
    c.close()


def _act(conn, d: str, km: float, pace: float = 360.0) -> int:
    cur = conn.execute(
        "INSERT INTO activity_summaries (source, source_id, name, activity_type, start_time,"
        " distance_m, duration_sec, avg_pace_sec_km) VALUES ('garmin', ?, 'Run', 'running', ?, ?, ?, ?)",
        (f"{d}-{km}", f"{d}T07:00:00", km * 1000, km * pace, pace))
    return cur.lastrowid


def _plan(conn, d: str, wtype: str, km: float | None, source: str = "planner",
          act_id: int | None = None, pace_min: int | None = None) -> int:
    cur = conn.execute(
        "INSERT INTO planned_workouts (date, workout_type, distance_km, source, matched_activity_id,"
        " target_pace_min, completed) VALUES (?, ?, ?, ?, ?, ?, 0)",
        (d, wtype, km, source, act_id, pace_min))
    pid = cur.lastrowid
    if act_id:
        actual = conn.execute("SELECT distance_m / 1000.0 FROM activity_summaries WHERE id=?", (act_id,)).fetchone()[0]
        conn.execute("INSERT INTO session_outcomes (planned_id, activity_id, date, actual_dist_km)"
                     " VALUES (?, ?, ?, ?)", (pid, act_id, d, actual))
    return pid


def _day(result, d: str) -> dict:
    return next(x for x in result["days"] if x["date"] == d)


def test_superseded_planner_row_not_in_denominator(conn):
    """외부 계획이 활동을 가져간 날은 외부 계획이 유효 — planner 원안은 대안으로 내려가 분모에서 빠진다."""
    a = _act(conn, "2026-09-27", 9.3)
    _plan(conn, "2026-09-27", "long", 22.4)
    _plan(conn, "2026-09-27", "easy", 10.0, source="garmin", act_id=a)
    r = wc.compute(conn, MON, date(2026, 9, 27), MON, TODAY)
    d = _day(r, "2026-09-27")
    assert d["effective"]["source"] == "garmin" and d["substituted"]
    assert d["state"] == "done" and d["label"] == "on_target"
    assert r["compliance"]["sessions"] == {"done": 1, "total": 1}


@pytest.mark.parametrize("actual, label, status", [
    (7.09, "under", "caution"), (10.0, "on_target", "excellent"), (12.5, "over", "good"),
])
def test_volume_labels(conn, actual, label, status):
    a = _act(conn, "2026-09-26", actual)
    _plan(conn, "2026-09-26", "long", 10.0, act_id=a)
    d = _day(wc.compute(conn, MON, date(2026, 9, 27), MON, TODAY), "2026-09-26")
    assert (d["label"], d["status"]) == (label, status)


def test_easy_run_too_fast_is_intensity_off(conn):
    """회복일에 목표보다 빠르게 달리면 거리가 많아도 '초과'가 아니라 '강도 어긋남'."""
    a = _act(conn, "2026-09-25", 8.3, pace=317)
    _plan(conn, "2026-09-25", "recovery", 6.9, act_id=a, pace_min=380)
    d = _day(wc.compute(conn, MON, date(2026, 9, 27), MON, TODAY), "2026-09-25")
    assert d["label"] == "intensity_off"


def test_missed_and_unplanned_run(conn):
    _act(conn, "2026-09-24", 10.0)
    _plan(conn, "2026-09-24", "interval", 5.7)
    r = wc.compute(conn, MON, date(2026, 9, 27), MON, TODAY)
    assert _day(r, "2026-09-24")["label"] == "missed"
    assert r["unplanned_runs"][0]["distance_km"] == 10.0
    assert r["compliance"]["quality"] == {"done": 0, "total": 1}
    assert r["compliance"]["volume"]["actual_km"] == 10.0  # 계획 외 러닝도 볼륨에 포함


def test_before_effective_start_is_pre_plan(conn):
    _plan(conn, "2026-09-22", "easy", 8.0)
    r = wc.compute(conn, MON, date(2026, 9, 27), date(2026, 9, 24), TODAY)
    assert _day(r, "2026-09-22")["state"] == "pre_plan"
    assert r["compliance"]["sessions"]["total"] == 0


def test_future_day_is_upcoming_and_not_counted(conn):
    _plan(conn, "2026-09-30", "easy", 8.0)
    r = wc.compute(conn, TODAY, date(2026, 10, 4), TODAY, TODAY)
    assert _day(r, "2026-09-30")["state"] == "upcoming"
    assert "label" not in _day(r, "2026-09-30")
    assert r["compliance"]["sessions"]["total"] == 0


def _accept(conn, wid: int, d: str, before: dict, after: dict) -> None:
    import json
    conn.execute(
        "INSERT INTO plan_adjustments(workout_id,date,source,before_json,after_json,rule_version,decision)"
        " VALUES (?,?,'crs',?,?,'adjuster_v1','accepted')", (wid, d, json.dumps(before), json.dumps(after)))


def test_accepted_rest_adjustment_leaves_denominator_and_run_is_unplanned(conn):
    a = _act(conn, "2026-09-24", 8.0)
    pid = _plan(conn, "2026-09-24", "interval", 8.0, act_id=a)
    _accept(conn, pid, "2026-09-24", {"workout_type": "interval", "distance_km": 8.0},
            {"workout_type": "rest", "distance_km": None})
    r = wc.compute(conn, MON, date(2026, 9, 27), MON, TODAY)
    d = _day(r, "2026-09-24")
    assert d["state"] == "rest" and d["effective"]["adjusted"]
    assert r["compliance"]["sessions"]["total"] == 0
    assert [u["activity_id"] for u in r["unplanned_runs"]] == [a]


def test_accepted_easy_adjustment_changes_quality_count(conn):
    pid = _plan(conn, "2026-09-24", "interval", 8.0)
    before = wc.compute(conn, MON, date(2026, 9, 27), MON, TODAY)["compliance"]["quality"]
    _accept(conn, pid, "2026-09-24", {"workout_type": "interval", "distance_km": 8.0}, {"workout_type": "easy"})
    after = wc.compute(conn, MON, date(2026, 9, 27), MON, TODAY)["compliance"]["quality"]
    assert before["total"] == 1 and after["total"] == 0


def test_user_skip_counts_as_missed_in_denominator(conn):
    import json
    pid = _plan(conn, "2026-09-24", "tempo", 8.0)
    conn.execute(
        "INSERT INTO plan_adjustments(workout_id,date,source,op,before_json,after_json,rule_version,decision)"
        " VALUES (?,?,'user','rest',?,?,'user_v1','accepted')",
        (pid, "2026-09-24", json.dumps({"workout_type": "tempo", "distance_km": 8.0}),
         json.dumps({"workout_type": "rest", "distance_km": None})))
    r = wc.compute(conn, MON, date(2026, 9, 27), MON, TODAY)
    c = r["compliance"]
    assert _day(r, "2026-09-24")["state"] == "skipped"
    assert c["sessions"] == {"done": 0, "total": 1}
    assert c["volume"]["planned_km"] == 8.0 and c["quality"]["total"] == 1
