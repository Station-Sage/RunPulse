"""plan_replace.replace_range — 보호 행 보존·proposed 조정 정리·외부 항목 보고."""
import sqlite3

import pytest

from src.db_setup import create_tables, migrate_db
from src.training.plan_replace import replace_range


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    migrate_db(c)
    return c


def _w(c, day, **kw):
    cols = {"completed": 0, "matched_activity_id": None, "garmin_workout_id": None, **kw}
    cur = c.execute("INSERT INTO planned_workouts(date,workout_type,distance_km,source,completed,matched_activity_id,"
                    "garmin_workout_id) VALUES (?, 'easy', 8.0, ?, ?, ?, ?)",
                    (day, kw.get("source", "planner"), cols["completed"], cols["matched_activity_id"], cols["garmin_workout_id"]))
    return cur.lastrowid


def _new(day):
    return {"date": day, "workout_type": "tempo", "distance_km": 10.0}


def test_replaces_unprotected_and_keeps_outside_range(conn):
    before = _w(conn, "2030-01-01")
    a = _w(conn, "2030-01-10")
    res = replace_range(conn, [_new("2030-01-10"), _new("2030-01-11")], "2030-01-08", "2030-01-14")
    assert [d["id"] for d in res["deleted"]] == [a] and len(res["inserted"]) == 2
    days = [r[0] for r in conn.execute("SELECT date FROM planned_workouts ORDER BY date")]
    assert days == ["2030-01-01", "2030-01-10", "2030-01-11"] and before


def test_protected_rows_survive_and_block_same_date(conn):
    done = _w(conn, "2030-01-10", completed=1)
    matched = _w(conn, "2030-01-11", matched_activity_id=5)
    outc = _w(conn, "2030-01-12")
    conn.execute("INSERT INTO session_outcomes(planned_id, date) VALUES (?, '2030-01-12')", (outc,))
    adj = _w(conn, "2030-01-13")
    conn.execute("INSERT INTO plan_adjustments(workout_id,date,source,op,before_json,after_json,rule_version,decision)"
                 " VALUES (?, '2030-01-13','user','rest','{}','{}','t','accepted')", (adj,))
    free = _w(conn, "2030-01-14")
    res = replace_range(conn, [_new(f"2030-01-{d}") for d in range(10, 15)], "2030-01-08", "2030-01-14")
    assert {p["id"] for p in res["preserved"]} == {done, matched, outc, adj}
    assert [d["id"] for d in res["deleted"]] == [free]
    assert res["skipped_dates"] == ["2030-01-10", "2030-01-11", "2030-01-12", "2030-01-13"]
    assert len(res["inserted"]) == 1


def test_proposed_adjustment_removed_with_row_and_external_reported(conn):
    a = _w(conn, "2030-01-10", garmin_workout_id="G1")
    conn.execute("INSERT INTO plan_adjustments(workout_id,date,source,op,before_json,after_json,rule_version)"
                 " VALUES (?, '2030-01-10','crs','replace','{}','{}','t')", (a,))
    res = replace_range(conn, [], "2030-01-08", "2030-01-14")
    assert conn.execute("SELECT count(*) FROM plan_adjustments").fetchone()[0] == 0
    assert res["external"] == [{"id": a, "date": "2030-01-10", "garmin_workout_id": "G1"}]


def test_manual_rows_untouched_and_no_commit(conn):
    m = _w(conn, "2030-01-10", source="manual")
    conn.commit()
    replace_range(conn, [_new("2030-01-11")], "2030-01-08", "2030-01-14")
    assert conn.execute("SELECT id FROM planned_workouts WHERE source='manual'").fetchone()[0] == m
    conn.rollback()
    assert conn.execute("SELECT count(*) FROM planned_workouts").fetchone()[0] == 1
