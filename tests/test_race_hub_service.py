"""tests/test_race_hub_service.py — race_hub_service 단위 테스트."""
from __future__ import annotations

import sqlite3

import pytest

from src.db_setup import create_tables, migrate_db
from src.services.race_hub_service import bucket_for_distance, get_race_hub

DATE = "2026-09-24"


# ─────────────────────────────────────────────────────────────────────────────
# Fixture
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def conn(db_conn):
    return db_conn


def _seed_metric(c, date, metric_name, value):
    c.execute(
        "INSERT INTO metric_store"
        " (scope_type, scope_id, metric_name, category, provider,"
        "  numeric_value, text_value, json_value, confidence, is_primary)"
        " VALUES ('daily', ?, ?, 'prediction', 'runpulse:formula_v1', ?, NULL, NULL, NULL, 1)",
        (date, metric_name, value),
    )


def _seed_goal(c, name, race_date, distance_km, target_time_sec=None, status="active"):
    c.execute(
        "INSERT INTO goals (name, race_date, distance_km, target_time_sec, status)"
        " VALUES (?, ?, ?, ?, ?)",
        (name, race_date, distance_km, target_time_sec, status),
    )


# ─────────────────────────────────────────────────────────────────────────────
# bucket_for_distance
# ─────────────────────────────────────────────────────────────────────────────

def test_bucket_marathon():
    assert bucket_for_distance(42.195) == "marathon"


def test_bucket_marathon_near():
    assert bucket_for_distance(42.0) == "marathon"


def test_bucket_half():
    assert bucket_for_distance(21.0975) == "half"


def test_bucket_half_near():
    assert bucket_for_distance(21.1) == "half"


def test_bucket_10k():
    assert bucket_for_distance(10.0) == "10k"


def test_bucket_5k():
    assert bucket_for_distance(5.0) == "5k"


def test_bucket_none_out_of_range():
    assert bucket_for_distance(15.0) is None


def test_bucket_none_input():
    assert bucket_for_distance(None) is None


# ─────────────────────────────────────────────────────────────────────────────
# get_race_hub — goal 없음
# ─────────────────────────────────────────────────────────────────────────────

def test_no_goal_all_none(conn):
    result = get_race_hub(conn, DATE)
    assert result["goal"] is None
    assert result["prediction"] is None
    assert result["form"] is None


# ─────────────────────────────────────────────────────────────────────────────
# get_race_hub — 지난 날짜 목표만 있으면 goal None
# ─────────────────────────────────────────────────────────────────────────────

def test_past_goal_only_returns_none(conn):
    _seed_goal(conn, "춘천마라톤 2025", "2025-10-26", 42.195, status="active")
    conn.commit()
    result = get_race_hub(conn, DATE)
    assert result["goal"] is None


# ─────────────────────────────────────────────────────────────────────────────
# get_race_hub — 미래 목표 선택 (가장 가까운 것)
# ─────────────────────────────────────────────────────────────────────────────

def test_nearest_future_goal_selected(conn):
    _seed_goal(conn, "춘천마라톤", "2026-10-25", 42.195)
    _seed_goal(conn, "서울마라톤", "2027-03-15", 42.195)
    conn.commit()
    result = get_race_hub(conn, DATE)
    assert result["goal"] is not None
    assert result["goal"]["race_date"] == "2026-10-25"


def test_days_left_and_weeks_left(conn):
    _seed_goal(conn, "춘천마라톤", "2026-10-25", 42.195)
    conn.commit()
    result = get_race_hub(conn, DATE)
    assert result["goal"]["days_left"] == 31
    assert result["goal"]["weeks_left"] == 4


# ─────────────────────────────────────────────────────────────────────────────
# get_race_hub — 예측 + gap_sec + history
# ─────────────────────────────────────────────────────────────────────────────

def test_prediction_value_and_gap(conn):
    _seed_goal(conn, "춘천마라톤", "2026-10-25", 42.195, target_time_sec=14400)
    _seed_metric(conn, "2026-07-01", "race_pred_marathon_sec", 15750)
    _seed_metric(conn, "2026-08-15", "race_pred_marathon_sec", 15692)
    _seed_metric(conn, "2026-09-20", "race_pred_marathon_sec", 15692)
    conn.commit()
    result = get_race_hub(conn, DATE)
    pred = result["prediction"]
    assert pred is not None
    assert pred["bucket"] == "marathon"
    assert pred["value_sec"] == 15692
    assert pred["gap_sec"] == 15692 - 14400
    assert pred["as_of"] == "2026-09-20"


def test_prediction_history_ascending(conn):
    _seed_goal(conn, "춘천마라톤", "2026-10-25", 42.195, target_time_sec=14400)
    _seed_metric(conn, "2026-07-01", "race_pred_marathon_sec", 15750)
    _seed_metric(conn, "2026-08-15", "race_pred_marathon_sec", 15692)
    _seed_metric(conn, "2026-09-20", "race_pred_marathon_sec", 15692)
    conn.commit()
    result = get_race_hub(conn, DATE)
    history = result["prediction"]["history"]
    assert len(history) == 3
    dates = [h["date"] for h in history]
    assert dates == sorted(dates)


def test_prediction_history_90d_window(conn):
    """기준일에서 90일 이상 된 데이터는 history에서 제외."""
    _seed_goal(conn, "춘천마라톤", "2026-10-25", 42.195, target_time_sec=14400)
    _seed_metric(conn, "2026-01-01", "race_pred_marathon_sec", 16000)  # 90일 초과
    _seed_metric(conn, "2026-09-01", "race_pred_marathon_sec", 15700)  # 90일 이내
    conn.commit()
    result = get_race_hub(conn, DATE)
    history = result["prediction"]["history"]
    dates = [h["date"] for h in history]
    assert "2026-01-01" not in dates
    assert "2026-09-01" in dates


# ─────────────────────────────────────────────────────────────────────────────
# get_race_hub — 목표 거리가 버킷 밖 → prediction None
# ─────────────────────────────────────────────────────────────────────────────

def test_no_bucket_no_prediction(conn):
    _seed_goal(conn, "15K 레이스", "2026-10-25", 15.0)
    conn.commit()
    result = get_race_hub(conn, DATE)
    assert result["goal"] is not None
    assert result["prediction"] is None


# ─────────────────────────────────────────────────────────────────────────────
# get_race_hub — target_time_sec None → gap_sec None
# ─────────────────────────────────────────────────────────────────────────────

def test_no_target_gap_is_none(conn):
    _seed_goal(conn, "춘천마라톤", "2026-10-25", 42.195, target_time_sec=None)
    _seed_metric(conn, "2026-09-20", "race_pred_marathon_sec", 15692)
    conn.commit()
    result = get_race_hub(conn, DATE)
    assert result["prediction"]["gap_sec"] is None


# ─────────────────────────────────────────────────────────────────────────────
# get_race_hub — form 반영
# ─────────────────────────────────────────────────────────────────────────────

def test_form_with_ctl_tsb(conn):
    _seed_goal(conn, "춘천마라톤", "2026-10-25", 42.195)
    conn.execute(
        "INSERT INTO metric_store"
        " (scope_type, scope_id, metric_name, category, provider,"
        "  numeric_value, text_value, json_value, confidence, is_primary)"
        " VALUES ('daily', ?, 'ctl', 'load', 'runpulse:formula_v1', 75.0, NULL, NULL, NULL, 1)",
        (DATE,),
    )
    conn.execute(
        "INSERT INTO metric_store"
        " (scope_type, scope_id, metric_name, category, provider,"
        "  numeric_value, text_value, json_value, confidence, is_primary)"
        " VALUES ('daily', ?, 'tsb', 'load', 'runpulse:formula_v1', -8.5, NULL, NULL, NULL, 1)",
        (DATE,),
    )
    conn.commit()
    result = get_race_hub(conn, DATE)
    assert result["form"]["ctl"] == 75.0
    assert result["form"]["tsb"] == -8.5


def test_form_no_metrics_both_none(conn):
    _seed_goal(conn, "춘천마라톤", "2026-10-25", 42.195)
    conn.commit()
    result = get_race_hub(conn, DATE)
    assert result["form"] == {"ctl": None, "tsb": None}


def test_hub_includes_projection_key(conn):
    conn.execute(
        "INSERT INTO goals (name, race_date, distance_km, status) VALUES ('R', '2026-10-25', 42.195, 'active')"
    )
    _seed_metric(conn, DATE, "ctl", 40)
    _seed_metric(conn, DATE, "atl", 55)
    hub = get_race_hub(conn, DATE)
    assert hub["projection"]["days_left"] == 31
    assert get_race_hub(conn, "2026-10-26")["projection"] is None


# ── race_briefing ─────────────────────────────────────────────────────────

from src.services.race_hub_service import form_band, race_briefing  # noqa: E402


def _hub(days_left, taper_tsb=None):
    proj = None
    if taper_tsb is not None:
        proj = {"scenarios": [{"key": "taper", "tsb": taper_tsb}, {"key": "keep", "tsb": 0}]}
    return {"goal": {"name": "춘천", "days_left": days_left}, "projection": proj}


def test_form_band_boundaries():
    # 경계는 src/metrics/bands.py(레이스 국면): 상한 미만 기준
    assert form_band(-31) == "과부하"
    assert form_band(-20) == "피로 누적"
    assert form_band(-10) == "유지"
    assert form_band(5) == "레이스 최적"
    assert form_band(24.9) == "레이스 최적"
    assert form_band(26) == "휴식 과다"


def test_race_briefing_none_without_goal_or_tsb():
    assert race_briefing({"goal": None}, -5) is None
    assert race_briefing(_hub(20), None) is None


def test_race_briefing_phases():
    assert "오늘이 레이스" in race_briefing(_hub(0), 0)[0]
    assert "레이스 주간" in race_briefing(_hub(5), 0)[0]
    assert "테이퍼 구간" in race_briefing(_hub(15, 12.7), -5)[0]
    build_tired, ev = race_briefing(_hub(31, 12.7), -28)
    assert "레이스까지 31일" in build_tired and "회복 위주" in build_tired
    assert "+13(레이스 최적)" in build_tired
    assert ev[0]["label"] == "춘천 D-31"
    assert ev[1]["label"] == "레이스 아침 TSB +13 (테이퍼 시)"
    assert "가볍게" in race_briefing(_hub(31), -15)[0]
    assert "핵심 세션" in race_briefing(_hub(31), -3)[0]


def test_today_briefing_uses_race_context(db_conn):
    from src.services.today_service import get_today_briefing
    db_conn.execute(
        "INSERT INTO goals (name, race_date, distance_km, status) VALUES ('R', '2026-10-25', 42.195, 'active')"
    )
    _seed_metric(db_conn, DATE, "tsb", -28)
    _seed_metric(db_conn, DATE, "ctl", 38)
    _seed_metric(db_conn, DATE, "atl", 66)
    b = get_today_briefing(db_conn, DATE)
    assert "레이스까지 31일" in b["headline"]
    assert b["evidence"][0]["metric"] == "race_days_left"
    assert b["evidence"][0]["drill"] is None
