"""tests/test_adjuster.py — adjuster 단위 테스트."""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

import pytest

from src.db_setup import create_tables, migrate_db
from src.training.adjuster import adjust_todays_plan


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.execute("PRAGMA foreign_keys=ON")
    create_tables(c)
    migrate_db(c)
    yield c
    c.close()


def _seed_workout(conn, target_date: str, workout_type: str = "long"):
    conn.execute(
        "INSERT INTO planned_workouts (date, workout_type, distance_km, completed, source)"
        " VALUES (?, ?, 10.0, 0, 'planner')",
        (target_date, workout_type),
    )
    conn.commit()


def _seed_wellness(conn, target_date: str, body_battery: int = 80, sleep_score: int = 75):
    conn.execute(
        "INSERT OR REPLACE INTO daily_wellness (date, body_battery_high, sleep_score)"
        " VALUES (?, ?, ?)",
        (target_date, body_battery, sleep_score),
    )
    conn.commit()


def _seed_tsb(conn, target_date: str, tsb_value: float):
    conn.execute(
        "INSERT OR REPLACE INTO metric_store"
        " (scope_type, scope_id, metric_name, provider, numeric_value, is_primary)"
        " VALUES ('daily', ?, 'tsb', 'runpulse', ?, 1)",
        (target_date, tsb_value),
    )
    conn.commit()


# ── 기본 동작 ────────────────────────────────────────────────────────────────

def test_adjust_returns_none_no_plan(conn):
    assert adjust_todays_plan(conn) is None


def test_adjust_returns_dict_with_plan(conn):
    today = date.today().isoformat()
    _seed_workout(conn, today)
    result = adjust_todays_plan(conn)
    assert result is not None
    assert "workout_type" in result
    assert "adjusted" in result
    assert "adjustment_reason_parts" in result
    assert isinstance(result["adjustment_reason_parts"], list)


def test_adjustment_reason_parts_is_list(conn):
    today = date.today().isoformat()
    _seed_workout(conn, today, "interval")
    _seed_wellness(conn, today, body_battery=25, sleep_score=35)
    _seed_tsb(conn, today, -20.0)

    result = adjust_todays_plan(conn)
    assert result is not None
    assert isinstance(result["adjustment_reason_parts"], list)
    # 피로도 높을 때 reason_parts에 각 지표가 들어가야 함
    assert len(result["adjustment_reason_parts"]) > 0


# ── date 파라미터 ─────────────────────────────────────────────────────────────

def test_adjust_past_date_uses_that_dates_data(conn):
    """과거 날짜 조회 시 그 날의 웰니스/TSB를 사용해야 한다 (오늘 값 아님)."""
    past = (date.today() - timedelta(days=3)).isoformat()
    today = date.today().isoformat()

    _seed_workout(conn, past, "interval")

    # 과거: 매우 높은 피로
    _seed_wellness(conn, past, body_battery=20, sleep_score=30)
    _seed_tsb(conn, past, -28.0)

    # 오늘: 컨디션 양호
    _seed_wellness(conn, today, body_battery=90, sleep_score=85)
    _seed_tsb(conn, today, 5.0)

    result = adjust_todays_plan(conn, date=past)
    assert result is not None
    # 과거 데이터 기반이면 피로도 high → interval → rest
    assert result["fatigue_level"] == "high"
    assert result["adjusted"] is True
    assert result["adjusted_type"] == "rest"


def test_adjust_today_default_unchanged(conn):
    """date=None은 오늘을 조회하는 기존 동작과 동일해야 한다."""
    today = date.today().isoformat()
    _seed_workout(conn, today, "easy")
    r1 = adjust_todays_plan(conn)
    r2 = adjust_todays_plan(conn, date=None)
    assert (r1 is None) == (r2 is None)
    if r1 is not None:
        assert r1["fatigue_level"] == r2["fatigue_level"]


def test_adjust_past_date_no_plan_returns_none(conn):
    """과거 날짜에 계획이 없으면 None."""
    past = (date.today() - timedelta(days=10)).isoformat()
    assert adjust_todays_plan(conn, date=past) is None
