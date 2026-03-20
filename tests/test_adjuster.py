"""adjuster.py 테스트."""

from datetime import date

import pytest

from src.training.adjuster import _fatigue_level, adjust_todays_plan


# ── 단위 테스트 ──────────────────────────────────────────────────────────────

def test_fatigue_low_no_data():
    assert _fatigue_level({}, None) == "low"


def test_fatigue_high_low_battery():
    wellness = {"body_battery": 20, "sleep_score": 30}
    assert _fatigue_level(wellness, tsb=-30) == "high"


def test_fatigue_moderate_bad_tsb_only():
    """TSB -28 단독: score=2 → moderate (high는 score>=4 필요)."""
    assert _fatigue_level({}, tsb=-28) == "moderate"


def test_fatigue_moderate_mid_battery():
    wellness = {"body_battery": 40}
    assert _fatigue_level(wellness, tsb=-18) == "moderate"


def test_fatigue_low_good_condition():
    wellness = {"body_battery": 80, "sleep_score": 75}
    assert _fatigue_level(wellness, tsb=5) == "low"


# ── 통합 테스트 ──────────────────────────────────────────────────────────────

def _insert_today_workout(conn, workout_type: str = "interval"):
    today = date.today().isoformat()
    conn.execute(
        """INSERT INTO planned_workouts
           (date, workout_type, distance_km, description, rationale, source)
           VALUES (?, ?, 8.0, '화요일 인터벌', '고강도', 'planner')""",
        (today, workout_type),
    )
    conn.commit()


def test_adjust_no_plan_returns_none(db_conn):
    assert adjust_todays_plan(db_conn) is None


def test_adjust_no_wellness_no_tsb(db_conn):
    """웰니스/TSB 없으면 계획 그대로 반환."""
    _insert_today_workout(db_conn, "interval")
    result = adjust_todays_plan(db_conn)
    assert result is not None
    assert result["adjusted"] is False
    assert result["fatigue_level"] == "low"


def test_adjust_high_fatigue_interval_to_rest(db_conn):
    _insert_today_workout(db_conn, "interval")
    today = date.today().isoformat()
    db_conn.execute(
        "INSERT INTO daily_wellness (date, source, body_battery, sleep_score) VALUES (?, 'garmin', 20, 30)",
        (today,),
    )
    db_conn.execute(
        "INSERT INTO daily_fitness (date, source, tsb) VALUES (?, 'intervals', -28)",
        (today,),
    )
    db_conn.commit()

    result = adjust_todays_plan(db_conn)
    assert result["adjusted"] is True
    assert result["adjusted_type"] == "rest"
    assert result["fatigue_level"] == "high"
    assert result["adjustment_reason"] is not None


def test_adjust_high_fatigue_long_to_easy(db_conn):
    """피로도 높음: long → easy (완전 rest는 아님)."""
    _insert_today_workout(db_conn, "long")
    today = date.today().isoformat()
    db_conn.execute(
        "INSERT INTO daily_wellness (date, source, body_battery, sleep_score) VALUES (?, 'garmin', 18, 25)",
        (today,),
    )
    db_conn.execute(
        "INSERT INTO daily_fitness (date, source, tsb) VALUES (?, 'intervals', -30)",
        (today,),
    )
    db_conn.commit()

    result = adjust_todays_plan(db_conn)
    assert result["adjusted_type"] == "easy"


def test_adjust_moderate_fatigue_tempo_to_easy(db_conn):
    _insert_today_workout(db_conn, "tempo")
    today = date.today().isoformat()
    db_conn.execute(
        "INSERT INTO daily_wellness (date, source, body_battery, sleep_score) VALUES (?, 'garmin', 42, 55)",
        (today,),
    )
    db_conn.commit()

    result = adjust_todays_plan(db_conn)
    assert result["adjusted_type"] == "easy"
    assert result["fatigue_level"] == "moderate"


def test_adjust_volume_boost(db_conn):
    """TSB > 10, body_battery > 70이면 volume_boost=True."""
    _insert_today_workout(db_conn, "easy")
    today = date.today().isoformat()
    db_conn.execute(
        "INSERT INTO daily_wellness (date, source, body_battery) VALUES (?, 'garmin', 85)",
        (today,),
    )
    db_conn.execute(
        "INSERT INTO daily_fitness (date, source, tsb) VALUES (?, 'intervals', 12.0)",
        (today,),
    )
    db_conn.commit()

    result = adjust_todays_plan(db_conn)
    assert result["volume_boost"] is True
    assert result["adjusted"] is False


def test_adjust_rest_not_boosted(db_conn):
    """rest 계획은 volume_boost 없음."""
    _insert_today_workout(db_conn, "rest")
    today = date.today().isoformat()
    db_conn.execute(
        "INSERT INTO daily_wellness (date, source, body_battery) VALUES (?, 'garmin', 90)",
        (today,),
    )
    db_conn.execute(
        "INSERT INTO daily_fitness (date, source, tsb) VALUES (?, 'intervals', 15.0)",
        (today,),
    )
    db_conn.commit()

    result = adjust_todays_plan(db_conn)
    assert result["volume_boost"] is False


def test_adjust_returns_wellness_and_tsb(db_conn):
    """결과에 wellness, tsb 컨텍스트 포함 확인."""
    _insert_today_workout(db_conn, "easy")
    today = date.today().isoformat()
    db_conn.execute(
        "INSERT INTO daily_wellness (date, source, body_battery, sleep_score) VALUES (?, 'garmin', 65, 70)",
        (today,),
    )
    db_conn.execute(
        "INSERT INTO daily_fitness (date, source, tsb) VALUES (?, 'intervals', -5.0)",
        (today,),
    )
    db_conn.commit()

    result = adjust_todays_plan(db_conn)
    assert "wellness" in result
    assert result["wellness"]["body_battery"] == 65
    assert result["tsb"] == -5.0
