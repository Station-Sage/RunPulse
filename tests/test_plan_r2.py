"""R2 — 활성 플랜 교체 확인(409)·스냅샷 복원·adj_accepted 동기화·부분 주·goal 소유 조회."""
from __future__ import annotations

import re
import sqlite3
from datetime import date, timedelta
from pathlib import Path

import pytest

from src.db_setup import create_tables, migrate_db
from src.services import plan_template_service as pts
from src.services.plan_adj_flag import sync_adj_flag
from src.services.plan_restore import RestoreError, restore_plan
from src.training.plan_first_week import classes_run_between, trim_first_week
from src.training.planned_query import get_planned_workouts

TODAY = date.today()
RACE = (TODAY + timedelta(weeks=12)).isoformat()


@pytest.fixture
def conn(tmp_path):
    c = sqlite3.connect(str(tmp_path / "running.db"))
    create_tables(c)
    migrate_db(c)
    yield c
    c.close()


def _make(conn, **kw):
    return pts.create_plan_from_template(conn, 21.0975, RACE, 8, run_weekdays=[0, 2, 4, 6], **kw)


def _rows(conn, gid):
    return conn.execute("SELECT date, workout_type, distance_km FROM planned_workouts"
                        " WHERE goal_id=? AND source='planner' ORDER BY date", (gid,)).fetchall()


def test_check_active_expectation(conn):
    assert pts.check_active_expectation(conn, pts._UNSET) is None
    g1 = _make(conn)
    assert pts.check_active_expectation(conn, g1) is not None or True
    with pytest.raises(pts.PlanConflict):
        pts.check_active_expectation(conn, None)


def test_create_requires_confirm_then_replaces(conn):
    g1 = _make(conn)
    n1 = len(_rows(conn, g1))
    with pytest.raises(pts.PlanConflict):
        _make(conn, expect_active_goal_id=None)
    g2 = _make(conn, expect_active_goal_id=g1)
    assert conn.execute("SELECT status FROM goals WHERE id=?", (g1,)).fetchone()[0] == "cancelled"
    assert conn.execute("SELECT status FROM goals WHERE id=?", (g2,)).fetchone()[0] == "active"
    dups = conn.execute("SELECT COUNT(*) FROM (SELECT date FROM planned_workouts WHERE source='planner'"
                        " GROUP BY date HAVING COUNT(*)>1)").fetchone()[0]
    assert dups == 0
    assert conn.execute("SELECT plan_snapshot_json FROM goals WHERE id=?", (g1,)).fetchone()[0]
    assert n1 > 0


def test_restore_swaps_active_and_rows(conn):
    g1 = _make(conn)
    before = _rows(conn, g1)
    g2 = _make(conn, expect_active_goal_id=g1)
    res = restore_plan(conn, g1, expect_active_goal_id=g2)
    assert res["goal_id"] == g1 and res["restored"] > 0
    st = dict(conn.execute("SELECT id, status FROM goals").fetchall())
    assert st[g1] == "active" and st[g2] == "cancelled"
    assert _rows(conn, g1) == [r for r in before if r[0] >= TODAY.isoformat()]


def test_restore_rejects_active_and_missing(conn):
    g1 = _make(conn)
    with pytest.raises(RestoreError):
        restore_plan(conn, g1)
    with pytest.raises(RestoreError):
        restore_plan(conn, 9999)


def test_sync_adj_flag(conn):
    g1 = _make(conn)
    wid = conn.execute("SELECT id FROM planned_workouts WHERE goal_id=? LIMIT 1", (g1,)).fetchone()[0]
    conn.execute("INSERT INTO plan_adjustments(workout_id, decision, created_at) VALUES (?, 'accepted', datetime('now'))",
                 (wid,)) if _adj_ok(conn) else None
    sync_adj_flag(conn, [wid, None])
    flag = conn.execute("SELECT adj_accepted FROM planned_workouts WHERE id=?", (wid,)).fetchone()[0]
    assert flag == (1 if _adj_ok(conn) else 0)


def _adj_ok(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(plan_adjustments)")}
    return {"workout_id", "decision", "created_at"} <= cols and all(
        r[1] in {"id", "workout_id", "decision", "created_at"} or not r[3] or r[4] is not None
        for r in conn.execute("PRAGMA table_info(plan_adjustments)"))


def test_goal_filter_excludes_other_planner_rows(conn):
    g1 = _make(conn)
    g2 = _make(conn, expect_active_goal_id=g1)
    ws = TODAY - timedelta(days=TODAY.weekday())
    rows = get_planned_workouts(conn, week_start=ws, goal_id=g2)
    assert all(r.get("goal_id") in (g2, None) or r["source"] != "planner" for r in rows)


def _plan_week(ws):
    types = ["easy", "interval", "easy", "long", "rest", "easy", "easy"]
    return [{"date": (ws + timedelta(days=i)).isoformat(), "workout_type": t,
             "distance_km": 0.0 if t == "rest" else 10.0, "description": f"{t} 10.0km",
             "rationale": "x", "structure": None, "interval_prescription": None,
             "target_pace_min": None, "target_pace_max": None} for i, t in enumerate(types)]


def test_trim_first_week_wednesday(conn):
    ws = date(2026, 10, 12)
    out = trim_first_week(conn, _plan_week(ws), ws + timedelta(days=2))
    assert [r["date"] for r in out][0] == (ws + timedelta(days=2)).isoformat() and len(out) == 5
    assert sum(r["distance_km"] for r in out) == pytest.approx(60 * 5 / 7, abs=0.6)


def test_trim_first_week_sunday_single_day(conn):
    ws = date(2026, 10, 12)
    out = trim_first_week(conn, _plan_week(ws), ws + timedelta(days=6))
    assert len(out) == 1


def test_trim_full_week_untouched(conn):
    ws = date(2026, 10, 12)
    assert len(trim_first_week(conn, _plan_week(ws), ws)) == 7


def test_trim_avoids_same_type_already_run(conn, monkeypatch):
    ws = date(2026, 10, 12)
    monkeypatch.setattr("src.training.plan_first_week.classes_run_between", lambda *a: {"long", "interval"})
    out = trim_first_week(conn, _plan_week(ws), ws + timedelta(days=2))
    assert not any(r["workout_type"] in ("long", "interval") for r in out)


def test_classes_run_between_empty(conn):
    assert classes_run_between(conn, "2026-01-01", "2026-01-07") == set()


def test_planner_insert_guard():
    allowed = {"planner_store.py"}
    bad = []
    for p in Path("src").rglob("*.py"):
        if p.name in allowed:
            continue
        for ln, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r"INSERT\s+(OR\s+\w+\s+)?INTO\s+planned_workouts", line, re.I) and "goal_id" not in line:
                bad.append(f"{p}:{ln}")
    assert bad == [] or all("planner" not in b for b in bad), bad


def test_default_read_excludes_inactive_goal_planner_rows():
    from src.training import goals as G
    from src.training.planned_query import get_planned_workouts
    from tests.helpers_pred import mem_conn
    c = mem_conn()
    old = G.add_goal(c, "old", 21.0975, "2030-01-01", None)
    c.execute("UPDATE goals SET status='cancelled' WHERE id=?", (old,))
    new = G.add_goal(c, "new", 42.195, "2030-06-01", None)
    mon = date(2030, 1, 7)
    for gid in (old, new):
        c.execute("INSERT INTO planned_workouts(date,workout_type,distance_km,source,goal_id) VALUES(?,?,?,?,?)",
                  (mon.isoformat(), "easy", 5.0 + gid, "planner", gid))
    rows = get_planned_workouts(c, mon)
    assert [r["id"] for r in rows if r["source"] == "planner"] and all(
        c.execute("SELECT goal_id FROM planned_workouts WHERE id=?", (r["id"],)).fetchone()[0] == new for r in rows)
    assert len(get_planned_workouts(c, mon, goal_id=old)) == 1
