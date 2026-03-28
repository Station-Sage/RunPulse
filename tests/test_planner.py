"""planner.py 테스트 (v2 — 논문 기반 재설계 반영)."""

from datetime import date, timedelta

import pytest

from src.training.goals import add_goal
from src.training.planner import (
    _training_phase,
    _weekly_volume_km,
    generate_weekly_plan,
    get_planned_workouts,
    save_weekly_plan,
    upsert_user_training_prefs,
)


# ── 단위 테스트 ──────────────────────────────────────────────────────────────

def test_training_phase_base():
    assert _training_phase(None, 0) == "base"
    assert _training_phase(20, 0) == "base"


def test_training_phase_build():
    assert _training_phase(12, 0) == "build"


def test_training_phase_peak():
    assert _training_phase(5, 0) == "peak"


def test_training_phase_taper():
    assert _training_phase(2, 0) == "taper"
    assert _training_phase(0, 0) == "taper"


def test_training_phase_recovery_week():
    """3:1 사이클 회복주 (Foster 1998)."""
    assert _training_phase(20, 3) == "recovery_week"


def test_weekly_volume_base_low_ctl():
    vol = _weekly_volume_km(ctl=10, phase="base", tsb=0, shape_pct=None)
    assert 20 <= vol <= 35


def test_weekly_volume_taper_reduces():
    # Mujika & Padilla 2003: 테이퍼 40~55% 감소
    normal = _weekly_volume_km(ctl=50, phase="build", tsb=0, shape_pct=None)
    taper = _weekly_volume_km(ctl=50, phase="taper", tsb=0, shape_pct=None)
    assert taper < normal * 0.65


def test_weekly_volume_high_fatigue_reduces():
    # Coggan 2003: TSB < -30 → 볼륨 감소
    normal = _weekly_volume_km(ctl=50, phase="build", tsb=0, shape_pct=None)
    tired = _weekly_volume_km(ctl=50, phase="build", tsb=-35, shape_pct=None)
    assert tired < normal


def test_weekly_volume_recovery_week():
    # Foster 1998 3:1 사이클: 회복주 볼륨 감소
    normal = _weekly_volume_km(ctl=50, phase="build", tsb=0, shape_pct=None)
    recovery = _weekly_volume_km(ctl=50, phase="recovery_week", tsb=0, shape_pct=None)
    assert recovery < normal


# ── 통합 테스트 ──────────────────────────────────────────────────────────────

def test_generate_weekly_plan_no_goal(db_conn):
    plan = generate_weekly_plan(db_conn)
    assert len(plan) == 7
    dates = [w["date"] for w in plan]
    assert len(set(dates)) == 7


def test_generate_weekly_plan_has_required_keys(db_conn):
    plan = generate_weekly_plan(db_conn)
    required = {"date", "workout_type", "description", "rationale", "source"}
    for w in plan:
        assert required.issubset(w.keys())
        assert w["source"] == "planner"


def test_generate_weekly_plan_valid_types(db_conn):
    valid = {"rest", "easy", "tempo", "interval", "long", "recovery"}
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
    monday = date(2026, 4, 6)
    plan = generate_weekly_plan(db_conn, week_start=monday)
    assert plan[0]["date"] == "2026-04-06"
    assert plan[6]["date"] == "2026-04-12"


def test_generate_weekly_plan_rest_weekday(db_conn):
    """사용자 지정 휴식 요일 반영."""
    monday = date(2026, 4, 6)
    # 월(bit0=1) + 금(bit4=16) = 17
    upsert_user_training_prefs(db_conn, rest_weekdays_mask=17)
    plan = generate_weekly_plan(db_conn, week_start=monday)
    assert plan[0]["workout_type"] == "rest"  # 월요일
    assert plan[4]["workout_type"] == "rest"  # 금요일


def test_generate_weekly_plan_blocked_date(db_conn):
    """일회성 차단 날짜 반영."""
    monday = date(2026, 4, 6)
    upsert_user_training_prefs(db_conn, blocked_dates=["2026-04-08"])
    plan = generate_weekly_plan(db_conn, week_start=monday)
    wed = next(w for w in plan if w["date"] == "2026-04-08")
    assert wed["workout_type"] == "rest"


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
    assert len(saved) == 7


def test_get_planned_workouts_empty(db_conn):
    assert get_planned_workouts(db_conn) == []


def test_save_weekly_plan_empty(db_conn):
    assert save_weekly_plan(db_conn, []) == 0


def test_generate_with_fitness_data(db_conn):
    """daily_fitness 데이터 있을 때 볼륨 증가."""
    db_conn.execute(
        "INSERT INTO daily_fitness (date, source, ctl, atl, tsb) VALUES (?, 'intervals', ?, ?, ?)",
        ("2026-03-20", 55.0, 60.0, -5.0),
    )
    db_conn.commit()
    plan = generate_weekly_plan(db_conn)
    assert len(plan) == 7
    # CTL=55 → 볼륨 증가 (기본값 25km보다 커야)
    total = sum(w["distance_km"] or 0 for w in plan)
    assert total > 25
