"""v2 콜드스타트 시작 부하(DESIGN-U16-LONGRUN §5.2)."""
from datetime import date, timedelta

from src.training import planner_schedule as S
from src.training.goals import add_goal
from tests.helpers_pred import mem_conn, seed_run

RACE = "2030-11-24"


def test_cold_start_km_sources():
    assert S.cold_start_km("half", 0.0, 0.0) == (16.0, "default")
    assert S.cold_start_km("full", 0.0, 0.0) == (20.0, "default")
    assert S.cold_start_km("10k", 0.0, 0.0) == (12.0, "default")
    assert S.cold_start_km("full", 0.0, 30.0) == (18.0, "avg16")         # 16주 평균 × 0.6
    assert S.cold_start_km("half", 0.0, 0.0, user_km=5.0) == (12.0, "user")   # 12km 미만은 12로


def test_cold_start_km_week1_limited_by_history():
    assert S.cold_start_km("full", 7.4, 30.0) == (12.0, "avg16")         # max(1.10×7.4, 12)
    assert S.cold_start_km("full", 11.5, 30.0) == (12.6, "avg16")        # 1.10×11.5 = 12.65 → 12.6


def test_recent_avg_km():
    c = mem_conn()
    for i in range(8):
        seed_run(c, sid=str(i), date=(date(2030, 6, 2) - timedelta(weeks=i + 1)).isoformat(), dist=16000.0)
    c.commit()
    assert S.recent_avg_km(c, date(2030, 6, 2), 16) == 8.0


def test_start_load_cold_only_for_v2():
    c = mem_conn()
    assert S.start_load(c, "half", date(2030, 6, 2), 1) == (0.0, 0.0, "history")
    assert S.start_load(c, "half", date(2030, 6, 2), 2) == (16.0, 10.0, "default")    # 롱런은 절대 최소에서


def _goal(c, rv):
    gid = add_goal(c, "g", 21.0975, RACE, None, rules_version=rv)
    c.execute("UPDATE goals SET plan_weeks=12, distance_label='half' WHERE id=?", (gid,))
    return {"id": gid, "race_date": RACE, "plan_weeks": 12, "distance_km": 21.0975}


def test_schedule_for_goal_cold_v2_not_empty_v1_empty():
    c = mem_conn()
    v1, v2 = _goal(c, 1), _goal(c, 2)
    assert S.schedule_for_goal(c, v1, "half", None, date(2030, 1, 1)) == []
    sched = S.schedule_for_goal(c, v2, "half", None, date(2030, 1, 1))
    assert len(sched) == 12 and sched[0].weekly_km == 16.0
    assert S.plan_start_source(c, v2, "half", date(2030, 1, 1)) == "default"
    assert S.plan_start_source(c, v1, "half", date(2030, 1, 1)) == "history"
