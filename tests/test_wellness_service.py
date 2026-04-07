"""tests/test_wellness_service.py — Phase 5-C 서비스 레이어 테스트."""
import pytest

from src.services.wellness_service import get_wellness_detail, get_wellness_trend

DATE = "2026-04-03"


@pytest.fixture
def conn(db_conn):
    c = db_conn

    c.execute("""
        INSERT INTO daily_wellness
            (date, sleep_score, sleep_duration_sec, hrv_weekly_avg, hrv_last_night,
             resting_hr, body_battery_high, body_battery_low, avg_stress, steps, weight_kg)
        VALUES (?, 82, 25920, 39.0, 42.0, 52, 78, 25, 32, 8500, 68.5)
    """, (DATE,))
    c.execute("""
        INSERT INTO daily_wellness (date, sleep_score, hrv_last_night, resting_hr)
        VALUES ('2026-04-02', 75, 38.0, 54)
    """)

    wellness_metrics = [
        ("daily", DATE, "utrs",  "readiness",    "runpulse:formula_v1", 72.3, None, None, 0.8, 1),
        ("daily", DATE, "cirs",  "readiness",    "runpulse:formula_v1", 28.1, None, None, None, 1),
        ("daily", DATE, "hrss",  "load",         "runpulse:formula_v1", 95.1, None, None, 0.9, 1),
    ]
    c.executemany(
        "INSERT INTO metric_store"
        " (scope_type, scope_id, metric_name, category, provider,"
        "  numeric_value, text_value, json_value, confidence, is_primary)"
        " VALUES (?,?,?,?,?,?,?,?,?,?)",
        wellness_metrics,
    )
    c.commit()
    return c


# get_wellness_detail

def test_get_wellness_detail_full(conn):
    result = get_wellness_detail(conn, DATE)
    assert result["date"] == DATE
    assert "core" in result
    assert "metrics_by_category" in result
    assert "readiness_summary" in result


def test_get_wellness_detail_core(conn):
    result = get_wellness_detail(conn, DATE)
    assert result["core"]["sleep_score"] == 82
    assert result["core"]["resting_hr"] == 52


def test_get_wellness_detail_metrics_by_category(conn):
    result = get_wellness_detail(conn, DATE)
    mbc = result["metrics_by_category"]
    # "readiness" 카테고리에 utrs, cirs 포함
    assert "readiness" in mbc
    names = [m["metric_name"] for m in mbc["readiness"]]
    assert "utrs" in names
    assert "cirs" in names


def test_get_wellness_detail_readiness_summary(conn):
    result = get_wellness_detail(conn, DATE)
    rs = result["readiness_summary"]
    assert rs["utrs"]["value"] == 72.3
    assert rs["cirs"]["value"] == 28.1


def test_get_wellness_detail_no_data(db_conn):
    result = get_wellness_detail(db_conn, DATE)
    assert result["core"] == {}
    assert result["metrics_by_category"] == {}
    assert result["readiness_summary"]["utrs"] is None


def test_get_wellness_detail_default_date(conn):
    result = get_wellness_detail(conn, None)
    assert "date" in result


# get_wellness_trend

def test_get_wellness_trend_full(conn):
    result = get_wellness_trend(conn, days=3650)
    assert "dates" in result
    assert "sleep_score" in result
    assert "hrv_last_night" in result
    assert "resting_hr" in result
    assert "utrs" in result
    assert len(result["dates"]) >= 2


def test_get_wellness_trend_includes_utrs(conn):
    result = get_wellness_trend(conn, days=3650)
    idx = result["dates"].index(DATE)
    assert result["utrs"][idx] == 72.3


def test_get_wellness_trend_with_gaps(conn):
    """날짜가 다른 wellness 행 + utrs — 날짜 정렬 확인."""
    result = get_wellness_trend(conn, days=3650)
    assert result["dates"] == sorted(result["dates"])


def test_get_wellness_trend_empty(db_conn):
    result = get_wellness_trend(db_conn, days=30)
    assert result["dates"] == []
    assert result["sleep_score"] == []
    assert result["utrs"] == []
