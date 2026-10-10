"""교차훈련으로 대체한 날은 이행률 분모에서 제외(E10)."""
from datetime import date, timedelta

from src.training import week_compliance as WC
from tests.helpers_pred import mem_conn

MON = date(2026, 9, 7)


def _plan(c, d, km=10.0):
    c.execute("INSERT INTO planned_workouts (date, workout_type, distance_km, source, completed) VALUES (?,?,?,?,0)",
              (d.isoformat(), "easy", km, "planner"))


def test_cross_day_excluded_from_denominator():
    c = mem_conn()
    _plan(c, MON)
    _plan(c, MON + timedelta(days=1))
    c.execute("INSERT INTO activity_summaries (source, source_id, activity_type, start_time, distance_m) "
              "VALUES ('garmin','b','cycling',?,30000)", ((MON + timedelta(days=1)).isoformat() + "T07:00:00",))
    out = WC.compute(c, MON, MON + timedelta(days=6), MON, today=MON + timedelta(days=3))
    states = {d["date"]: d["state"] for d in out["days"]}
    assert states[MON.isoformat()] == "missed" and states[(MON + timedelta(days=1)).isoformat()] == "cross"
    assert out["compliance"]["sessions"]["total"] == 1
    assert out["compliance"]["volume"]["planned_km"] == 10.0
