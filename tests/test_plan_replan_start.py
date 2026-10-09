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
    out2 = R.preview(c, {"recent_long_km": 21}, TODAY)
    assert out2["start_long_km"] == 21
