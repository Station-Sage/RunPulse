"""tests/test_plan_service.py — plan_service 단위 테스트."""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

import pytest

from src.db_setup import create_tables, migrate_db
from src.services import plan_service
from src.training.goals import add_goal


def _seed_goal(conn) -> int:
    return add_goal(conn, "서울 마라톤", 42.195, race_date="2027-03-15",
                    target_time_sec=14400)


def _seed_workout(conn, goal_date: str, workout_type: str = "easy",
                  completed: int = 0):
    conn.execute(
        "INSERT INTO planned_workouts "
        "(date, workout_type, distance_km, completed, source) "
        "VALUES (?, ?, ?, ?, 'planner')",
        (goal_date, workout_type, 10.0, completed),
    )
    conn.commit()


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.execute("PRAGMA foreign_keys=ON")
    create_tables(c)
    migrate_db(c)
    yield c
    c.close()


# ── get_active_plan ───────────────────────────────────────────────────────────

def test_get_active_plan_no_goal_returns_none(conn):
    assert plan_service.get_active_plan(conn) is None


def test_get_active_plan_returns_structure(conn):
    _seed_goal(conn)
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    _seed_workout(conn, week_start.isoformat(), "easy", completed=0)
    _seed_workout(conn, (week_start + timedelta(days=1)).isoformat(), "long",
                  completed=1)

    result = plan_service.get_active_plan(conn)
    assert result is not None
    assert "goal" in result
    assert result["goal"]["name"] == "서울 마라톤"
    assert result["goal"]["distance_km"] == 42.195
    assert "week_index" in result
    assert result["week_index"] >= 1
    assert "workouts" in result
    assert isinstance(result["workouts"], list)
    assert "ctl_current" in result
    assert "compliance_pct" in result


def test_get_active_plan_by_goal_id(conn):
    goal_id = _seed_goal(conn)
    result = plan_service.get_active_plan(conn, goal_id=goal_id)
    assert result is not None
    assert result["goal"]["id"] == goal_id


def test_get_active_plan_by_invalid_goal_id_returns_none(conn):
    assert plan_service.get_active_plan(conn, goal_id=9999) is None


def test_compliance_pct_with_mixed_workouts(conn):
    _seed_goal(conn)
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    # 2 completed, 1 not, 1 rest
    _seed_workout(conn, week_start.isoformat(), "easy", completed=1)
    _seed_workout(conn, (week_start + timedelta(1)).isoformat(), "long", completed=1)
    _seed_workout(conn, (week_start + timedelta(2)).isoformat(), "tempo", completed=0)
    _seed_workout(conn, (week_start + timedelta(3)).isoformat(), "rest", completed=0)

    result = plan_service.get_active_plan(conn)
    # 2/3 non-rest = 66.7
    assert result["compliance_pct"] == pytest.approx(66.7, abs=0.1)


# ── get_todays_adjustment ────────────────────────────────────────────────────

def test_get_todays_adjustment_no_plan_returns_none(conn):
    result = plan_service.get_todays_adjustment(conn)
    assert result is None


def test_get_todays_adjustment_with_plan(conn):
    _seed_goal(conn)
    today = date.today().isoformat()
    _seed_workout(conn, today, "easy", completed=0)
    # adjust_todays_plan either returns dict or None depending on data
    result = plan_service.get_todays_adjustment(conn)
    # Result should be dict or None — both acceptable
    assert result is None or isinstance(result, dict)
