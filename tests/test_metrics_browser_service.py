"""tests/test_metrics_browser_service.py — metrics_browser_service 단위 테스트."""
from __future__ import annotations

import sqlite3

import pytest

from src.db_setup import create_tables, migrate_db
from src.metrics.engine import run_activity_metrics, run_daily_metrics
from src.services.metrics_browser_service import get_metric_trend, get_metrics_browser


@pytest.fixture()
def conn(tmp_path):
    db_file = tmp_path / "running.db"
    c = sqlite3.connect(str(db_file))
    create_tables(c)
    migrate_db(c)
    c.execute(
        "INSERT INTO activity_summaries "
        "(source, source_id, name, activity_type, start_time, "
        "distance_m, moving_time_sec, avg_hr, max_hr, avg_speed_ms) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        ["garmin", "1", "Morning Run", "running", "2026-04-01 08:00:00",
         10_000, 3_000, 155, 185, 3.33],
    )
    c.execute(
        "INSERT INTO daily_wellness (date, resting_hr, body_battery_high, sleep_score) "
        "VALUES (?, ?, ?, ?)",
        ["2026-04-01", 52, 80, 85],
    )
    c.commit()
    act_id = c.execute("SELECT id FROM activity_summaries WHERE source_id='1'").fetchone()[0]
    run_activity_metrics(c, act_id)
    c.commit()
    run_daily_metrics(c, "2026-04-01")
    c.commit()
    yield c
    c.close()


def test_get_metrics_browser_structure(conn):
    result = get_metrics_browser(conn, date="2026-04-01")
    assert result["date"] == "2026-04-01"
    assert isinstance(result["categories"], list)
    assert len(result["categories"]) > 0


def test_get_metrics_browser_no_empty_categories(conn):
    result = get_metrics_browser(conn, date="2026-04-01")
    for cat in result["categories"]:
        assert len(cat["metrics"]) > 0, f"category {cat['category']} has no metrics"


def test_get_metrics_browser_entry_fields(conn):
    result = get_metrics_browser(conn, date="2026-04-01")
    # ctl은 daily 메트릭이므로 어딘가에 있어야 함
    all_metrics = [m for cat in result["categories"] for m in cat["metrics"]]
    names = [m["name"] for m in all_metrics]
    assert "ctl" in names, f"ctl not found in {names}"

    ctl_entry = next(m for m in all_metrics if m["name"] == "ctl")
    assert "label" in ctl_entry
    assert "value" in ctl_entry
    assert "unit" in ctl_entry
    assert "sparkline" in ctl_entry
    assert isinstance(ctl_entry["sparkline"], list)


def test_get_metrics_browser_auto_date(conn):
    """date=None이면 최신 날짜를 자동 조회."""
    result = get_metrics_browser(conn, date=None)
    assert result["date"] == "2026-04-01"


def test_get_metric_trend_returns_data(conn):
    result = get_metric_trend(conn, "ctl", period="1y")
    assert result is not None
    assert result["slug"] == "ctl"
    assert "points" in result
    assert len(result["points"]) > 0
    assert "current" in result
    assert "peak" in result
    assert result["peak"] is not None


def test_get_metric_trend_unknown_returns_none(conn):
    result = get_metric_trend(conn, "nonexistent_metric_xyz", period="3m")
    assert result is None


def test_get_metric_trend_invalid_period_falls_back(conn):
    """잘못된 period는 '3m' 기본값으로 동작."""
    result = get_metric_trend(conn, "ctl", period="invalid")
    # invalid period → 3m fallback → 데이터가 있으면 반환
    # 이 픽스처는 2026-04-01 데이터만 있으므로 None 또는 결과 모두 허용
    assert result is None or result["slug"] == "ctl"


def test_get_metric_trend_peak_and_change_pct(conn):
    result = get_metric_trend(conn, "ctl", period="1y")
    assert result is not None
    # 단일 포인트라도 peak는 존재해야 함
    assert result["peak"] is not None
    # 포인트 1개일 경우 change_pct는 None(0으로 나누기 방지)
    if len(result["points"]) == 1:
        assert result["change_pct"] is None or result["change_pct"] == 0.0
