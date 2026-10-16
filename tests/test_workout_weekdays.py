"""운동 요일 필수화(PLN-11/12) · 주간 정합화(PLN-4) 단위 테스트."""
from datetime import date, timedelta

import pytest

from src.training import goals as G
from src.training.plan_finalize import finalize_week, week_violations
from src.training.planner import generate_weekly_plan
from src.training.planner_config import WeekdaysRequired, resolve_run_weekdays, weekdays_to_mask
from src.training.planner_store import ensure_user_training_prefs, set_workout_weekdays
from tests.helpers_pred import mem_conn, with_days

MON = date(2026, 10, 12)


def _row(i, t, km, desc=None):
    d = MON + timedelta(days=i)
    return {"date": d.isoformat(), "workout_type": t, "distance_km": km,
            "description": desc if desc is not None else f"{t} {km}km", "rationale": "x", "structure": None}


def test_set_workout_weekdays_stores_mask():
    c = mem_conn()
    assert set_workout_weekdays(c, [0, 2, 4]) == weekdays_to_mask([0, 2, 4])
    assert c.execute("SELECT workout_weekdays_mask FROM user_training_prefs").fetchone()[0] == 0b0010101


@pytest.mark.parametrize("days", [[], None, [7], [-1, 2]])
def test_set_workout_weekdays_rejects_invalid(days):
    with pytest.raises(WeekdaysRequired):
        set_workout_weekdays(mem_conn(), days)


def test_resolve_requires_mask():
    c = mem_conn()
    ensure_user_training_prefs(c)
    from src.training.planner_config import load_prefs
    prefs = load_prefs(c)
    with pytest.raises(WeekdaysRequired):
        resolve_run_weekdays(prefs)


def test_generate_without_mask_raises():
    with pytest.raises(WeekdaysRequired):
        generate_weekly_plan(mem_conn(), week_start=MON)


def test_generate_respects_specified_weekdays():
    c = with_days(mem_conn(), [1, 3, 5])
    plan = generate_weekly_plan(c, week_start=MON)
    run_days = {date.fromisoformat(r["date"]).weekday() for r in plan if r["workout_type"] not in ("rest", "race")}
    assert run_days <= {1, 3, 5}
    assert week_violations(plan, [1, 3, 5]) == []


def test_week_violations_detects_each_kind():
    rows = [_row(0, "rest", 5.0, "rest"), _row(1, "easy", 6.0, "easy 9.0km"), _row(2, "easy", 6.0)]
    v = week_violations(rows, [1, 2])
    assert any("휴식인데 거리" in x for x in v)
    assert any("설명" in x for x in v)
    rows2 = [_row(0, "easy", 6.0)]
    assert any("지정하지 않은 요일" in x for x in week_violations(rows2, [3]))


def test_finalize_week_fixes_weekday_and_rest_distance():
    rows = [_row(0, "easy", 6.0), _row(1, "rest", 4.0, "rest"), _row(2, "easy", 6.0)]
    finalize_week(rows, run_weekdays=[2])
    assert rows[0]["workout_type"] == "rest" and rows[0]["distance_km"] == 0.0
    assert rows[1]["distance_km"] == 0.0
    assert rows[2]["workout_type"] == "easy" and rows[2]["distance_km"] == 6.0


def test_finalize_week_skips_race_rows():
    rows = [_row(0, "race", 42.195, "race")]
    finalize_week(rows, run_weekdays=[3])
    assert rows[0]["workout_type"] == "race" and rows[0]["distance_km"] == 42.195


def test_plan_weeks_counts_inclusive_and_rejects_past():
    today = date.today()
    race = today + timedelta(weeks=10)
    assert G._plan_weeks(race.isoformat()) in (10, 11)
    assert G._plan_weeks((today - timedelta(weeks=3)).isoformat()) is None
    assert G._plan_weeks("not-a-date") is None


def test_backtest_scenario_without_mask_raises():
    from src.training.plan_backtest import Scenario, engine_v1
    scn = Scenario("grid", "half", 12, "2030-11-24", 4)
    with pytest.raises(ValueError):
        engine_v1(scn, mem_conn())


def test_auto_paths_skip_without_mask():
    from src.services import weekly_adapt_job
    from src.training.rematch import replan_future
    c = mem_conn()
    today = date.today()
    gid = G.add_goal(c, "g", 21.0975, (today + timedelta(weeks=8)).isoformat(), None)
    assert weekly_adapt_job.run(c, today) == 0
    r = replan_future(c, gid, today)
    assert r["regenerated"] == 0 and "skipped" in r
    assert c.execute("SELECT COUNT(*) FROM planned_workouts").fetchone()[0] == 0
