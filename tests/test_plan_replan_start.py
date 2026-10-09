"""재계획 시작점 근거 — 상태 A/B/C/D 출처·basis, 롱런 미입력 시 이력값 저장 (DESIGN-PLAN-A6-REPLAN-UI §11)."""
from datetime import date, timedelta

import pytest

from src.services import plan_replan_service as R
from src.training.goals import add_goal
from tests.helpers_pred import mem_conn, seed_run

TODAY = date.today()
RACE = (R.next_monday(TODAY) + timedelta(weeks=10, days=5)).isoformat()


@pytest.fixture
def c():
    conn = mem_conn()
    gid = add_goal(conn, "g", 21.0975, RACE, 7200, rules_version=2)
    conn.execute("UPDATE goals SET plan_weeks=14, distance_label='half' WHERE id=?", (gid,))
    conn.commit()
    return conn


def _runs(conn, weeks_back, km_per_week, long_km=None):
    for w in weeks_back:
        d = (TODAY - timedelta(weeks=w, days=1)).isoformat()
        seed_run(conn, sid=f"s{w}", date=d, dist=(long_km or km_per_week) * 1000)
        if not long_km:
            continue
        seed_run(conn, sid=f"t{w}", date=(TODAY - timedelta(weeks=w, days=2)).isoformat(),
                 dist=(km_per_week - long_km) * 1000)


def test_state_a_history_ignores_low_input(c):
    _runs(c, [1, 2, 3, 4], 32, long_km=18)
    out = R.preview(c, {"recent_weekly_km": 10}, TODAY)
    assert out["start_source"] == "history" and out["basis"]["km4"] >= 12
    assert out["start_km"] >= out["basis"]["km4"]
    assert out["goal_target_time_sec"] == 7200


def test_state_b_floor(c):
    _runs(c, [1, 2], 8)
    out = R.preview(c, {"recent_weekly_km": 40}, TODAY)
    assert out["start_source"] == "floor" and 0 < out["basis"]["km4"] < 12 and out["start_km"] == 12.0


def test_state_c_gap_uses_avg16_or_user(c):
    _runs(c, [8, 9, 10, 11, 12, 13], 40)
    out = R.preview(c, {}, TODAY)
    assert out["basis"]["km4"] == 0 and out["start_source"] == "avg16"
    assert R.preview(c, {"recent_weekly_km": 25}, TODAY)["start_source"] == "user"


def test_state_d_new_user_default(c):
    out = R.preview(c, {}, TODAY)
    assert out["start_source"] == "default" and out["basis"] == {"km4": 0.0, "avg16": 0.0, "long6": 0.0, "long12": 0.0}
    assert out["start_long_km"] is None


def test_blank_long_stores_history_long_and_real_source(c):
    _runs(c, [1, 2, 3, 4], 32, long_km=18)
    out = R.apply(c, {"recent_weekly_km": 50, "expect_anchor": R.next_monday(TODAY).isoformat()}, TODAY)
    row = c.execute("SELECT start_long_km, start_source FROM plan_replans WHERE id=?", (out["replan_id"],)).fetchone()
    assert out["start_long_km"] == row[0] == 18.0 and row[1] == "history"
    R.undo(c, out["replan_id"], TODAY)
    out2 = R.preview(c, {"recent_long_km": 21}, TODAY)
    assert out2["start_long_km"] == 21


def test_real_source_stored_and_loaded(c):
    from src.training.plan_anchor import load_anchors
    out = R.apply(c, {"recent_weekly_km": 25, "expect_anchor": R.next_monday(TODAY).isoformat()}, TODAY)
    assert c.execute("SELECT start_source FROM plan_replans WHERE id=?", (out["replan_id"],)).fetchone()[0] == "user"
    gid = c.execute("SELECT id FROM goals").fetchone()[0]
    assert load_anchors(c, gid)[0].start_source == "user"


def test_history_anchor_tail_not_raised_by_cold_peak(c):
    _runs(c, [1, 2, 3, 4], 32, long_km=18)
    out = R.preview(c, {}, TODAY)
    assert out["start_source"] == "history"
    peak = max(w["planned_km"] for w in out["after"])
    assert peak <= out["start_km"] * 1.6


def test_weekly_km_has_long_km(c):
    out = R.preview(c, {}, TODAY)
    assert all("long_km" in w for w in out["after"])
    assert any(w["long_km"] > 0 for w in out["after"])
    assert all(w["long_km"] <= w["planned_km"] for w in out["after"])


def _apply(conn):
    return R.apply(conn, {"expect_anchor": R.next_monday(TODAY).isoformat()}, TODAY)


def test_pending_blocks_second_replan_until_undone(c):
    out = _apply(c)
    with pytest.raises(R.ReplanError) as e:
        R.preview(c, {}, TODAY)
    assert e.value.code == "REPLAN_PENDING" and e.value.last["replan_id"] == out["replan_id"]
    R.undo(c, out["replan_id"], TODAY)
    assert R.preview(c, {}, TODAY)["replan_id"] is None
    _apply(c)


def test_history_on_new_rows_hides_undo_and_allows_replan(c):
    out = _apply(c)
    c.execute("UPDATE planned_workouts SET completed=1 WHERE source='planner' AND date=?",
              (R.next_monday(TODAY).isoformat(),))
    c.commit()
    assert R.last_undoable(c, TODAY) is None
    with pytest.raises(R.ReplanError) as e:
        R.undo(c, out["replan_id"], TODAY)
    assert e.value.code == "REPLAN_LOCKED"


def test_entry_state_rules(c):
    assert R.entry_state(c, TODAY) == {"eligible": True, "reason": None, "last": None}
    out = _apply(c)
    st = R.entry_state(c, TODAY)
    assert not st["eligible"] and st["reason"] == "PENDING" and st["last"]["replan_id"] == out["replan_id"]
    for days, ok in ((-2, False), (5, False), (12, True)):
        c.execute("UPDATE goals SET race_date=?", ((R.next_monday(TODAY) + timedelta(days=days)).isoformat(),))
        c.execute("UPDATE plan_replans SET status='undone'")
        st = R.entry_state(c, TODAY)
        assert st["eligible"] is ok, days
        assert ok or st["reason"] == "RACE_NEAR"
    c.execute("UPDATE goals SET status='completed'")
    assert R.entry_state(c, TODAY)["reason"] == "NO_GOAL"
