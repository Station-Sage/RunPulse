"""planner.py 테스트."""

from datetime import date, timedelta

import pytest

from src.training.goals import add_goal
from src.training.planner import (
    _long_run_km,
    _pick_template,
    _training_phase,
    _weekly_volume_km,
    generate_weekly_plan,
    get_planned_workouts,
    save_weekly_plan,
)


# ── 단위 테스트 ──────────────────────────────────────────────────────────────

def test_training_phase_base():
    assert _training_phase(None) == "base"
    assert _training_phase(20) == "base"


def test_training_phase_build():
    assert _training_phase(12) == "build"


def test_training_phase_peak():
    assert _training_phase(5) == "peak"


def test_training_phase_taper():
    assert _training_phase(2) == "taper"
    assert _training_phase(0) == "taper"


def test_weekly_volume_base_low_ctl():
    vol = _weekly_volume_km(ctl=10, phase="base", tsb=0)
    assert 20 <= vol <= 35


def test_weekly_volume_taper_reduces():
    normal = _weekly_volume_km(ctl=50, phase="build", tsb=0)
    taper = _weekly_volume_km(ctl=50, phase="taper", tsb=0)
    assert taper < normal


def test_weekly_volume_high_fatigue_reduces():
    normal = _weekly_volume_km(ctl=50, phase="build", tsb=0)
    tired = _weekly_volume_km(ctl=50, phase="build", tsb=-30)
    assert tired < normal


def test_long_run_marathon():
    km = _long_run_km(42.195, "build")
    assert km == 30.0


def test_long_run_taper():
    km = _long_run_km(42.195, "taper")
    assert km < 20.0


def test_pick_template_7_days():
    for dist in [5.0, 10.0, 21.1, 42.195]:
        tmpl = _pick_template(dist, "build")
        assert len(tmpl) == 7


def test_pick_template_has_rest():
    tmpl = _pick_template(42.195, "build")
    assert "rest" in tmpl


def test_pick_template_base_no_interval():
    """베이스 단계에는 인터벌 없음."""
    tmpl = _pick_template(42.195, "base")
    assert "interval" not in tmpl


def test_pick_template_taper_no_interval():
    tmpl = _pick_template(42.195, "taper")
    assert "interval" not in tmpl


# ── 통합 테스트 ──────────────────────────────────────────────────────────────

def test_generate_weekly_plan_no_goal(db_conn):
    plan = generate_weekly_plan(db_conn)
    assert len(plan) == 7
    dates = [w["date"] for w in plan]
    # 7개 날짜가 모두 다름
    assert len(set(dates)) == 7


def test_generate_weekly_plan_has_required_keys(db_conn):
    plan = generate_weekly_plan(db_conn)
    required = {"date", "workout_type", "description", "rationale", "source"}
    for w in plan:
        assert required.issubset(w.keys())
        assert w["source"] == "planner"


def test_generate_weekly_plan_valid_types(db_conn):
    valid = {"rest", "easy", "tempo", "interval", "long"}
    plan = generate_weekly_plan(db_conn)
    for w in plan:
        assert w["workout_type"] in valid


def test_generate_weekly_plan_with_goal(db_conn):
    gid = add_goal(db_conn, name="서울마라톤", distance_km=42.195,
                   race_date="2026-11-01")
    plan = generate_weekly_plan(db_conn, goal_id=gid)
    assert len(plan) == 7
    types = [w["workout_type"] for w in plan]
    assert "long" in types


def test_generate_weekly_plan_week_start(db_conn):
    monday = date(2026, 4, 6)  # 고정 월요일
    plan = generate_weekly_plan(db_conn, week_start=monday)
    assert plan[0]["date"] == "2026-04-06"
    assert plan[6]["date"] == "2026-04-12"


def test_save_and_get_planned_workouts(db_conn):
    monday = date(2026, 4, 6)
    plan = generate_weekly_plan(db_conn, week_start=monday)
    count = save_weekly_plan(db_conn, plan)
    assert count == 7

    saved = get_planned_workouts(db_conn, week_start=monday)
    assert len(saved) == 7


def test_save_weekly_plan_overwrites(db_conn):
    """같은 주에 두 번 generate하면 덮어씀."""
    monday = date(2026, 4, 6)
    plan1 = generate_weekly_plan(db_conn, week_start=monday)
    save_weekly_plan(db_conn, plan1)

    plan2 = generate_weekly_plan(db_conn, week_start=monday)
    save_weekly_plan(db_conn, plan2)

    saved = get_planned_workouts(db_conn, week_start=monday)
    assert len(saved) == 7  # 중복 없음


def test_get_planned_workouts_empty(db_conn):
    workouts = get_planned_workouts(db_conn)
    assert workouts == []


def test_save_weekly_plan_empty(db_conn):
    assert save_weekly_plan(db_conn, []) == 0


def test_generate_with_fitness_data(db_conn):
    """daily_fitness 데이터 있을 때 정상 작동."""
    db_conn.execute(
        "INSERT INTO daily_fitness (date, source, ctl, atl, tsb) VALUES (?, 'intervals', ?, ?, ?)",
        ("2026-03-20", 55.0, 60.0, -5.0),
    )
    db_conn.commit()
    plan = generate_weekly_plan(db_conn)
    assert len(plan) == 7
