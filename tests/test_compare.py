"""compare.py 테스트."""

import sqlite3
import pytest
from src.db_setup import create_tables
from src.analysis.compare import (
    compare_periods,
    compare_today_vs_yesterday,
    compare_this_week_vs_last,
    compare_this_month_vs_last,
    _calc_changes,
)


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    yield c
    c.close()


def _insert_activity(conn, source, source_id, start_time, distance_km=10.0,
                     duration_sec=3600, avg_pace=360, avg_hr=150,
                     matched_group_id=None):
    """테스트용 활동 삽입 헬퍼."""
    conn.execute("""
        INSERT INTO activity_summaries
            (source, source_id, start_time, distance_km, duration_sec,
             avg_pace_sec_km, avg_hr, activity_type, matched_group_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'running', ?)
    """, (source, source_id, start_time, distance_km, duration_sec,
          avg_pace, avg_hr, matched_group_id))
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def _insert_metric(conn, activity_id, source, metric_name, metric_value):
    conn.execute("""
        INSERT INTO activity_detail_metrics (activity_id, source, metric_name, metric_value)
        VALUES (?, ?, ?, ?)
    """, (activity_id, source, metric_name, metric_value))


# ── 기본 동작 ───────────────────────────────────────────────────────────

def test_compare_empty_periods(conn):
    """데이터 없을 때 0/None 반환."""
    result = compare_periods(conn, "2026-01-01", "2026-01-08",
                             "2026-01-08", "2026-01-15")
    assert result["period1"]["run_count"] == 0
    assert result["period2"]["run_count"] == 0
    assert result["delta"]["run_count"] == 0


def test_compare_basic_metrics(conn):
    """두 기간 기본 지표 비교."""
    _insert_activity(conn, "garmin", "g1", "2026-01-02T08:00:00",
                     distance_km=8.0, avg_pace=375, avg_hr=140)
    _insert_activity(conn, "garmin", "g2", "2026-01-09T08:00:00",
                     distance_km=10.0, avg_pace=360, avg_hr=145)

    result = compare_periods(conn, "2026-01-01", "2026-01-08",
                             "2026-01-08", "2026-01-15")

    assert result["period1"]["run_count"] == 1
    assert result["period2"]["run_count"] == 1
    assert result["period1"]["total_distance_km"] == 8.0
    assert result["period2"]["total_distance_km"] == 10.0
    assert result["delta"]["total_distance_km"] == 2.0
    assert result["pct"]["total_distance_km"] == 25.0


def test_dedup_by_matched_group_id(conn):
    """matched_group_id로 중복 활동을 하나로 취급."""
    _insert_activity(conn, "garmin", "g1", "2026-01-02T08:00:00",
                     distance_km=10.0, matched_group_id="group1")
    _insert_activity(conn, "strava", "s1", "2026-01-02T08:01:00",
                     distance_km=10.1, matched_group_id="group1")

    result = compare_periods(conn, "2026-01-01", "2026-01-08",
                             "2026-01-08", "2026-01-15")
    # 두 활동이 같은 그룹 → run_count = 1
    assert result["period1"]["run_count"] == 1


def test_source_metrics_garmin(conn):
    """Garmin 소스 지표 (training_effect, training_load) 집계."""
    act_id = _insert_activity(conn, "garmin", "g1", "2026-01-02T08:00:00")
    _insert_metric(conn, act_id, "garmin", "training_effect_aerobic", 3.5)
    _insert_metric(conn, act_id, "garmin", "training_load", 80.0)

    result = compare_periods(conn, "2026-01-01", "2026-01-08",
                             "2026-01-08", "2026-01-15")
    assert result["period1"]["garmin_training_effect_avg"] == pytest.approx(3.5)
    assert result["period1"]["garmin_training_load_total"] == pytest.approx(80.0)
    assert result["period2"]["garmin_training_load_total"] is None


def test_source_metrics_strava(conn):
    """Strava suffer_score 합계."""
    act_id = _insert_activity(conn, "strava", "s1", "2026-01-02T08:00:00")
    _insert_metric(conn, act_id, "strava", "relative_effort", 120.0)

    result = compare_periods(conn, "2026-01-01", "2026-01-08",
                             "2026-01-08", "2026-01-15")
    assert result["period1"]["strava_suffer_score_total"] == pytest.approx(120.0)


def test_last_day_metric(conn):
    """기간 마지막 날 지표 (intervals CTL) 반환."""
    a1 = _insert_activity(conn, "intervals", "i1", "2026-01-02T08:00:00")
    a2 = _insert_activity(conn, "intervals", "i2", "2026-01-06T08:00:00")
    _insert_metric(conn, a1, "intervals", "ctl", 50.0)
    _insert_metric(conn, a2, "intervals", "ctl", 55.0)

    result = compare_periods(conn, "2026-01-01", "2026-01-08",
                             "2026-01-08", "2026-01-15")
    # 마지막 날(01-06) 기준 CTL = 55.0
    assert result["period1"]["intervals_ctl_last"] == pytest.approx(55.0)


def test_delta_and_pct_none_when_missing(conn):
    """한쪽 기간 데이터 없으면 delta/pct = None."""
    _insert_activity(conn, "garmin", "g1", "2026-01-09T08:00:00")

    result = compare_periods(conn, "2026-01-01", "2026-01-08",
                             "2026-01-08", "2026-01-15")
    # period1 run_count=0, period2 run_count=1 → pct는 None (분모 0)
    assert result["delta"]["run_count"] == 1
    assert result["pct"]["run_count"] is None  # 0→1: 0 분모


def test_calc_changes_boundary():
    """_calc_changes 직접 테스트 - 0 분모 처리."""
    p1 = {"x": 0.0, "y": 10.0}
    p2 = {"x": 5.0, "y": 12.0}
    delta, pct = _calc_changes(p1, p2)
    assert delta["x"] == 5.0
    assert pct["x"] is None   # 분모 0
    assert delta["y"] == 2.0
    assert pct["y"] == 20.0


def test_convenience_functions_run(conn):
    """편의 함수들이 오류 없이 실행되는지 확인."""
    compare_today_vs_yesterday(conn)
    compare_this_week_vs_last(conn)
    compare_this_month_vs_last(conn)
