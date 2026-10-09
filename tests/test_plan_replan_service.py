"""plan_replan_service — preview 쓰기 없음, apply 보호 행 보존, undo 조건(ADR-035 부록 R)."""
from datetime import date, timedelta

import pytest

from src.services import plan_replan_service as R
from src.training.goals import add_goal
from src.training.planner import generate_weekly_plan, save_weekly_plan
from tests.helpers_pred import mem_conn

TODAY = date.today()
MON = R.next_monday(TODAY)
RACE = (MON + timedelta(weeks=10, days=5)).isoformat()


@pytest.fixture
def c():
    conn = mem_conn()
    gid = add_goal(conn, "g", 21.0975, RACE, None, rules_version=2)
    conn.execute("UPDATE goals SET plan_weeks=14, distance_label='half' WHERE id=?", (gid,))
    conn.commit()
    ws = MON - timedelta(weeks=1)
    for i in range(12):
        save_weekly_plan(conn, generate_weekly_plan(conn, gid, week_start=ws + timedelta(weeks=i)))
    return conn


def _count(conn):
    return conn.execute("SELECT count(*) FROM planned_workouts").fetchone()[0]


def test_preview_writes_nothing(c):
    snap = c.execute("SELECT id,date,distance_km FROM planned_workouts ORDER BY id").fetchall()
    out = R.preview(c, {"recent_weekly_km": 20}, TODAY)
    assert out["replan_id"] is None and out["anchor_monday"] == MON.isoformat() and out["after"]
    assert c.execute("SELECT count(*) FROM plan_replans").fetchone()[0] == 0
    assert c.execute("SELECT id,date,distance_km FROM planned_workouts ORDER BY id").fetchall() == snap


def test_apply_conflict_and_errors(c):
    with pytest.raises(R.ReplanError) as e:
        R.apply(c, {"expect_anchor": "2000-01-03"}, TODAY)
    assert e.value.code == "CONFLICT"
    with pytest.raises(R.ReplanError) as e:
        R.preview(c, {}, date.fromisoformat(RACE))
    assert e.value.code == "RACE_WEEK"
    c.execute("UPDATE goals SET status='cancelled'")
    with pytest.raises(R.ReplanError) as e:
        R.preview(c, {}, TODAY)
    assert e.value.code == "NO_GOAL"


def test_apply_protects_history_and_keeps_past(c):
    past = c.execute("SELECT id FROM planned_workouts WHERE date < ?", (MON.isoformat(),)).fetchall()
    done = c.execute("SELECT id FROM planned_workouts WHERE date >= ? ORDER BY date LIMIT 1", (MON.isoformat(),)).fetchone()[0]
    c.execute("UPDATE planned_workouts SET completed=1 WHERE id=?", (done,))
    c.commit()
    out = R.apply(c, {"recent_weekly_km": 20, "expect_anchor": MON.isoformat()}, TODAY)
    assert out["replan_id"] and [p["id"] for p in out["preserved"]] == [done]
    assert c.execute("SELECT count(*) FROM planned_workouts WHERE id=?", (done,)).fetchone()[0] == 1
    assert {r[0] for r in past} <= {r[0] for r in c.execute("SELECT id FROM planned_workouts")}
    assert c.execute("SELECT status FROM plan_replans").fetchone()[0] == "applied"


def test_undo_restores_and_locks(c):
    before = c.execute("SELECT date,workout_type,distance_km FROM planned_workouts ORDER BY date,id").fetchall()
    out = R.apply(c, {"recent_weekly_km": 20, "expect_anchor": MON.isoformat()}, TODAY)
    R.undo(c, out["replan_id"], TODAY)
    assert c.execute("SELECT date,workout_type,distance_km FROM planned_workouts ORDER BY date,id").fetchall() == before
    with pytest.raises(R.ReplanError) as e:
        R.undo(c, out["replan_id"], TODAY)
    assert e.value.code == "REPLAN_LOCKED"


def test_undo_locked_after_start_or_new_history(c):
    out = R.apply(c, {"expect_anchor": MON.isoformat()}, TODAY)
    with pytest.raises(R.ReplanError):
        R.undo(c, out["replan_id"], MON)
    c.execute("UPDATE planned_workouts SET completed=1 WHERE date=(SELECT min(date) FROM planned_workouts WHERE date>=?)",
              (MON.isoformat(),))
    with pytest.raises(R.ReplanError) as e:
        R.undo(c, out["replan_id"], TODAY)
    assert e.value.code == "REPLAN_LOCKED"


def test_last_undoable(c):
    assert R.last_undoable(c, TODAY) is None
    a = R.apply(c, {"recent_weekly_km": 20, "expect_anchor": MON.isoformat()}, TODAY)
    last = R.last_undoable(c, TODAY)
    assert last["replan_id"] == a["replan_id"] and last["undo_until"] == (MON - timedelta(days=1)).isoformat()
    assert R.last_undoable(c, MON) is None
    R.undo(c, a["replan_id"], TODAY)
    assert R.last_undoable(c, TODAY) is None
