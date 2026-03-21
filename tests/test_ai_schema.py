"""ai_schema 모듈 테스트."""
import pytest

from src.ai.ai_schema import normalize_workout, validate_weekly_plan


def _plan(workouts, week_start="2026-03-23"):
    return {"week_start": week_start, "workouts": workouts}


# ── validate_weekly_plan ──────────────────────────────────────────────────────

def test_validate_valid_plan():
    plan = _plan([
        {"date": "2026-03-23", "type": "easy", "distance_km": 8.0},
        {"date": "2026-03-24", "type": "rest"},
    ])
    ok, errors = validate_weekly_plan(plan)
    assert ok
    assert errors == []


def test_validate_not_dict():
    ok, errors = validate_weekly_plan("string")
    assert not ok
    assert "dict" in errors[0]


def test_validate_no_workouts():
    ok, errors = validate_weekly_plan({"week_start": "2026-03-23"})
    assert not ok


def test_validate_invalid_type():
    plan = _plan([{"date": "2026-03-23", "type": "sprint"}])
    ok, errors = validate_weekly_plan(plan)
    assert not ok
    assert any("sprint" in e for e in errors)


def test_validate_invalid_date():
    plan = _plan([{"date": "not-a-date", "type": "easy"}])
    ok, errors = validate_weekly_plan(plan)
    assert not ok


def test_validate_distance_out_of_range():
    plan = _plan([{"date": "2026-03-23", "type": "easy", "distance_km": 999}])
    ok, errors = validate_weekly_plan(plan)
    assert not ok
    assert any("범위" in e for e in errors)


def test_validate_too_many_workouts():
    workouts = [{"date": f"2026-03-2{i}", "type": "easy", "distance_km": 5.0}
                for i in range(8)]
    ok, errors = validate_weekly_plan({"workouts": workouts})
    assert not ok
    assert any("초과" in e for e in errors)


def test_validate_rest_no_distance_ok():
    plan = _plan([{"date": "2026-03-23", "type": "rest"}])
    ok, errors = validate_weekly_plan(plan)
    assert ok


# ── normalize_workout ─────────────────────────────────────────────────────────

def test_normalize_uses_type_key():
    w = {"date": "2026-03-23", "type": "tempo", "distance_km": "10"}
    n = normalize_workout(w)
    assert n["workout_type"] == "tempo"
    assert n["distance_km"] == 10.0


def test_normalize_uses_workout_type_key():
    w = {"date": "2026-03-23", "workout_type": "interval", "distance_km": 5}
    n = normalize_workout(w)
    assert n["workout_type"] == "interval"


def test_normalize_source_is_ai():
    w = {"date": "2026-03-23", "type": "easy"}
    n = normalize_workout(w)
    assert n["source"] == "ai"


def test_normalize_none_distance():
    w = {"date": "2026-03-23", "type": "rest"}
    n = normalize_workout(w)
    assert n["distance_km"] is None
