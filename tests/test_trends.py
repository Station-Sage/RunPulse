"""trends.py 테스트."""

import sqlite3
import pytest
from src.db_setup import create_tables
from src.analysis.trends import (
    weekly_trends,
    calculate_acwr,
    fitness_trend,
    _acwr_status,
)


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    yield c
    c.close()


def _insert_activity(conn, source, source_id, start_time, distance_km=10.0,
                     duration_sec=3600, avg_pace=360, matched_group_id=None):
    conn.execute("""
        INSERT INTO activities
            (source, source_id, start_time, distance_km, duration_sec,
             avg_pace_sec_km, activity_type, matched_group_id)
        VALUES (?, ?, ?, ?, ?, ?, 'running', ?)
    """, (source, source_id, start_time, distance_km, duration_sec,
          avg_pace, matched_group_id))
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def _insert_metric(conn, activity_id, source, metric_name, metric_value):
    conn.execute("""
        INSERT INTO source_metrics (activity_id, source, metric_name, metric_value)
        VALUES (?, ?, ?, ?)
    """, (activity_id, source, metric_name, metric_value))


# ── weekly_trends ───────────────────────────────────────────────────────

def test_weekly_trends_empty(conn):
    """데이터 없을 때 8주 결과 반환, 거리 모두 0."""
    result = weekly_trends(conn, weeks=8)
    assert len(result) == 8
    for w in result:
        assert w["total_distance_km"] == 0.0
        assert w["run_count"] == 0


def test_weekly_trends_pct_change(conn):
    """주간 변화율 계산 확인."""
    # 2주 전 활동
    from datetime import date, timedelta
    today = date.today()
    two_weeks_ago_monday = today - timedelta(days=today.weekday() + 14)
    one_week_ago_monday = today - timedelta(days=today.weekday() + 7)

    _insert_activity(conn, "garmin", "g1",
                     f"{two_weeks_ago_monday.isoformat()}T08:00:00",
                     distance_km=20.0)
    _insert_activity(conn, "garmin", "g2",
                     f"{one_week_ago_monday.isoformat()}T08:00:00",
                     distance_km=24.0)

    result = weekly_trends(conn, weeks=4)
    # 변화율 20.0 확인 (20→24 = +20%)
    pcts = [w["pct_change_distance"] for w in result
            if w["pct_change_distance"] is not None]
    assert any(abs(p - 20.0) < 0.1 for p in pcts)


def test_weekly_trends_dedup(conn):
    """matched_group_id 중복 제거 확인."""
    from datetime import date, timedelta
    today = date.today()
    this_monday = today - timedelta(days=today.weekday())
    dt = f"{this_monday.isoformat()}T08:00:00"
    _insert_activity(conn, "garmin", "g1", dt, distance_km=10.0,
                     matched_group_id="grp1")
    _insert_activity(conn, "strava", "s1", dt, distance_km=10.1,
                     matched_group_id="grp1")

    result = weekly_trends(conn, weeks=1)
    assert result[0]["run_count"] == 1


# ── calculate_acwr ──────────────────────────────────────────────────────

def test_acwr_no_data(conn):
    """데이터 없으면 None 반환."""
    assert calculate_acwr(conn) is None


def test_acwr_single_source(conn):
    """단일 소스로 ACWR 계산."""
    from datetime import date, timedelta
    today = date.today()

    # 만성 기간(28일) 동안 garmin training_load 삽입
    for i in range(1, 29):
        d = today - timedelta(days=i)
        act_id = _insert_activity(conn, "garmin", f"g{i}",
                                  f"{d.isoformat()}T08:00:00")
        _insert_metric(conn, act_id, "garmin", "training_load", 60.0)

    result = calculate_acwr(conn, acute_days=7, chronic_days=28)
    assert result is not None
    assert "garmin_tl" in result
    assert "average" in result
    # acute=7*60=420, chronic=28*60=1680, chronic_daily=60, chronic_in_acute=7*60=420
    # ACWR = 420/420 = 1.0
    assert result["garmin_tl"]["acwr"] == pytest.approx(1.0, abs=0.01)
    assert result["garmin_tl"]["status"] == "safe"


def test_acwr_boundary_13(conn):
    """ACWR 정확히 1.3 경계값 테스트 (safe/caution 경계)."""
    assert _acwr_status(1.3) == "safe"
    assert _acwr_status(1.31) == "caution"


def test_acwr_boundary_15(conn):
    """ACWR 정확히 1.5 경계값 테스트 (caution/danger 경계)."""
    assert _acwr_status(1.5) == "caution"
    assert _acwr_status(1.51) == "danger"


def test_acwr_multiple_sources(conn):
    """복수 소스 ACWR 계산 및 평균."""
    from datetime import date, timedelta
    today = date.today()

    for i in range(1, 29):
        d = today - timedelta(days=i)
        a1 = _insert_activity(conn, "garmin", f"g{i}", f"{d.isoformat()}T07:00:00")
        _insert_metric(conn, a1, "garmin", "training_load", 60.0)
        a2 = _insert_activity(conn, "strava", f"s{i}", f"{d.isoformat()}T07:01:00")
        _insert_metric(conn, a2, "strava", "relative_effort", 100.0)

    result = calculate_acwr(conn)
    assert result is not None
    assert "garmin_tl" in result
    assert "strava_re" in result
    assert "average" in result
    # 두 소스 ACWR이 같으면 average도 동일
    assert result["average"]["acwr"] == pytest.approx(
        (result["garmin_tl"]["acwr"] + result["strava_re"]["acwr"]) / 2, abs=0.01
    )


# ── fitness_trend ───────────────────────────────────────────────────────

def test_fitness_trend_empty(conn):
    """데이터 없을 때 N주 결과, 지표 모두 None."""
    result = fitness_trend(conn, weeks=4)
    assert len(result) == 4
    for w in result:
        assert w["intervals_ctl"] is None
        assert w["runalyze_effective_vo2max"] is None


def test_fitness_trend_with_data(conn):
    """intervals CTL 데이터가 있을 때 반영 확인."""
    from datetime import date, timedelta
    today = date.today()
    this_monday = today - timedelta(days=today.weekday())
    act_id = _insert_activity(conn, "intervals", "i1",
                              f"{this_monday.isoformat()}T08:00:00")
    _insert_metric(conn, act_id, "intervals", "ctl", 65.0)

    result = fitness_trend(conn, weeks=2)
    last_week = result[-1]
    assert last_week["intervals_ctl"] == pytest.approx(65.0)
