import sqlite3
from datetime import date, timedelta

import pytest

from src.analysis.race_readiness import assess_race_readiness, vdot_race_predictions
from src.db_setup import create_tables


@pytest.fixture
def conn():
    conn = sqlite3.connect(":memory:")
    create_tables(conn)
    yield conn
    conn.close()


def _insert_daily(conn, d, source, **values):
    cols = ["date", "source"] + list(values.keys())
    q = ", ".join(["?"] * len(cols))
    conn.execute(
        f"INSERT INTO daily_fitness ({', '.join(cols)}) VALUES ({q})",
        [d, source] + list(values.values()),
    )


def _insert_wellness(
    conn,
    d,
    body_battery=75,
    sleep_score=80,
    hrv_value=50,
    stress_avg=30,
    resting_hr=52,
):
    conn.execute(
        """
        INSERT INTO daily_wellness
        (date, source, body_battery, sleep_score, hrv_value, stress_avg, resting_hr)
        VALUES (?, 'garmin', ?, ?, ?, ?, ?)
        """,
        (d, body_battery, sleep_score, hrv_value, stress_avg, resting_hr),
    )


def _insert_activity(conn, source, start_time, activity_type="running", distance_km=10.0, duration_sec=3000):
    source_id = f"{source}-{start_time}"
    cur = conn.execute(
        """
        INSERT INTO activity_summaries
        (source, source_id, activity_type, start_time, distance_km, duration_sec, avg_pace_sec_km)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (source, source_id, activity_type, start_time, distance_km, duration_sec, int(duration_sec / distance_km)),
    )
    return cur.lastrowid


def _insert_metric(conn, activity_id, source, metric_name, metric_value=None, metric_json=None):
    conn.execute(
        """
        INSERT INTO activity_detail_metrics (activity_id, source, metric_name, metric_value, metric_json)
        VALUES (?, ?, ?, ?, ?)
        """,
        (activity_id, source, metric_name, metric_value, metric_json),
    )


def test_readiness_full_data(conn):
    today = date.today()
    for i, v in enumerate([47.0, 47.4, 47.8, 48.2]):
        d = (today - timedelta(days=28 - i * 7)).isoformat()
        _insert_daily(conn, d, "garmin", garmin_vo2max=v)
        _insert_daily(conn, d, "runalyze", runalyze_evo2max=48 + i * 0.2, runalyze_vdot=45 + i * 0.3, runalyze_marathon_shape=82 + i)
        _insert_daily(conn, d, "intervals", ctl=42 + i * 2, atl=50 + i * 2, tsb=5)
    for i in range(1, 8):
        _insert_wellness(conn, (today - timedelta(days=i)).isoformat())
    act = _insert_activity(conn, "runalyze", today.isoformat() + "T08:00:00")
    _insert_metric(conn, act, "runalyze", "race_prediction", metric_json='{"5k":1200,"10k":2500}')
    conn.commit()

    result = assess_race_readiness(conn)
    assert result["status"] == "ok"
    assert result["readiness_score"] is not None
    assert result["grade"] in {"A", "B", "C", "D", "F"}
    assert "recommendation" in result
    assert result["data_sufficiency"] in {"enough", "high"}


def test_readiness_minimal_data_is_insufficient(conn):
    today = date.today().isoformat()
    _insert_daily(conn, today, "intervals", ctl=41)
    conn.commit()

    result = assess_race_readiness(conn)
    assert result["status"] == "insufficient_data"
    assert result["readiness_score"] is None
    assert result["grade"] is None
    assert result["scores"]["fitness_score"] >= 80
    assert "충분한 데이터가 쌓이지 않았습니다" in result["warning"]


def test_readiness_no_data(conn):
    result = assess_race_readiness(conn)
    assert result["status"] == "insufficient_data"
    assert result["readiness_score"] is None
    assert result["grade"] is None
    assert "충분한 데이터가 쌓이지 않았습니다" in result["warning"]


def test_grade_A_with_enough_data(conn):
    today = date.today()
    for i, v in enumerate([49, 50, 51, 52]):
        d = (today - timedelta(days=21 - i * 7)).isoformat()
        _insert_daily(conn, d, "garmin", garmin_vo2max=v)
        _insert_daily(conn, d, "runalyze", runalyze_evo2max=v, runalyze_vdot=50, runalyze_marathon_shape=92)
        _insert_daily(conn, d, "intervals", ctl=55, atl=58, tsb=5)
    for i in range(1, 8):
        _insert_wellness(conn, (today - timedelta(days=i)).isoformat(), body_battery=90, sleep_score=90, hrv_value=60, stress_avg=20, resting_hr=50)
    conn.commit()

    result = assess_race_readiness(conn)
    assert result["status"] == "ok"
    assert result["grade"] in {"A", "B"}


def test_days_to_race(conn):
    target = date.today() + timedelta(days=30)
    result = assess_race_readiness(conn, race_date=target.isoformat(), race_distance_km=42.195)
    assert result["days_to_race"] == 30
    assert result["race_distance_km"] == 42.195


def test_freshness_optimal(conn):
    today = date.today().isoformat()
    _insert_daily(conn, today, "intervals", ctl=40, tsb=5)
    _insert_daily(conn, today, "garmin", garmin_vo2max=49)
    _insert_daily(conn, today, "runalyze", runalyze_vdot=46)
    conn.commit()

    result = assess_race_readiness(conn)
    assert result["scores"]["freshness_score"] == 100.0


def test_freshness_over_rest(conn):
    today = date.today().isoformat()
    _insert_daily(conn, today, "intervals", ctl=40, tsb=18)
    _insert_daily(conn, today, "garmin", garmin_vo2max=49)
    _insert_daily(conn, today, "runalyze", runalyze_vdot=46)
    conn.commit()

    result = assess_race_readiness(conn)
    assert result["scores"]["freshness_score"] == 60.0


def test_recommendation_contains_weak(conn):
    today = date.today()
    for i in range(3):
        d = (today - timedelta(days=i * 7)).isoformat()
        _insert_daily(conn, d, "intervals", ctl=20, atl=40, tsb=-20)
        _insert_daily(conn, d, "garmin", garmin_vo2max=42)
        _insert_daily(conn, d, "runalyze", runalyze_vdot=40)
    conn.commit()

    result = assess_race_readiness(conn)
    assert result["recommendation"]
    assert ("기초 체력" in result["recommendation"]) or ("신선도" in result["recommendation"])


def test_vdot_race_predictions():
    preds = vdot_race_predictions(45)
    assert preds is not None
    assert 1100 <= preds["5k"] <= 1500
    assert 2300 <= preds["10k"] <= 3200
    assert 5000 <= preds["half"] <= 7500
    assert 10500 <= preds["full"] <= 15000


def test_vdot_none():
    assert vdot_race_predictions(None) is None
