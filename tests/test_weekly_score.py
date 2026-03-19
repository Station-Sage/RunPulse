"""weekly_score.py 테스트."""

import sqlite3
import pytest
from datetime import date, timedelta

from src.db_setup import create_tables
from src.analysis.weekly_score import (
    calculate_weekly_score,
    _volume_score,
    _intensity_score,
    _acwr_score,
    _recovery_comp_score,
    _consistency_score,
    _efficiency_score,
)


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    yield c
    c.close()


@pytest.fixture
def test_config():
    return {"user": {"weekly_distance_target": 40.0}}


def _insert_activity(conn, source, source_id, start_time, distance_km=10.0,
                     duration_sec=3600, avg_pace=360, avg_hr=150,
                     matched_group_id=None):
    conn.execute("""
        INSERT INTO activities
            (source, source_id, start_time, distance_km, duration_sec,
             avg_pace_sec_km, avg_hr, activity_type, matched_group_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'running', ?)
    """, (source, source_id, start_time, distance_km, duration_sec,
          avg_pace, avg_hr, matched_group_id))
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


# ── 개별 점수 함수 ──────────────────────────────────────────────────────

def test_volume_score_perfect():
    """목표 100% → 만점 25."""
    assert _volume_score(40.0, 40.0) == 25.0


def test_volume_score_90_percent():
    """목표 90% → 만점."""
    assert _volume_score(36.0, 40.0) == 25.0


def test_volume_score_110_percent():
    """목표 110% → 만점."""
    assert _volume_score(44.0, 40.0) == 25.0


def test_volume_score_under():
    """목표 미달 → 비례 감점."""
    score = _volume_score(20.0, 40.0)
    assert score < 25.0
    assert score > 0.0


def test_volume_score_zero_target():
    """목표 0이면 0점."""
    assert _volume_score(50.0, 0.0) == 0.0


def test_intensity_score_perfect():
    """Easy 80% → 만점 20."""
    assert _intensity_score(0.80) == 20.0


def test_intensity_score_none():
    """데이터 없으면 중간값 10."""
    assert _intensity_score(None) == 10.0


def test_intensity_boundary_75_85():
    """Easy 비율 75%~85% 경계."""
    assert _intensity_score(0.75) == 20.0
    assert _intensity_score(0.85) == 20.0
    assert _intensity_score(0.74) < 20.0


def test_acwr_score_perfect():
    """ACWR 1.0 → 만점 20."""
    assert _acwr_score(1.0) == 20.0


def test_acwr_score_none():
    """데이터 없으면 중간값 10."""
    assert _acwr_score(None) == 10.0


def test_acwr_score_boundary_08():
    """ACWR 0.8 → 만점 경계."""
    assert _acwr_score(0.8) == 20.0
    assert _acwr_score(0.79) < 20.0


def test_acwr_score_boundary_13():
    """ACWR 1.3 → 만점 경계."""
    assert _acwr_score(1.3) == 20.0
    assert _acwr_score(1.31) < 20.0


def test_recovery_comp_score_full():
    """회복 80점 → 만점 15."""
    assert _recovery_comp_score(80.0) == pytest.approx(15.0)


def test_recovery_comp_score_none():
    """데이터 없으면 7.5."""
    assert _recovery_comp_score(None) == 7.5


def test_consistency_score_perfect():
    """계획 == 실제 → 만점 10."""
    assert _consistency_score(4, 4) == 10.0


def test_consistency_score_zero_planned():
    """계획 0 → 5점 (중간)."""
    assert _consistency_score(3, 0) == 5.0


def test_efficiency_score_improved():
    """EF 개선 시 만점 10."""
    # prev EF = 360/150 = 2.4, curr EF = 350/150 ≈ 2.33 → 개선
    assert _efficiency_score(150, 350, 150, 360) == 10.0


def test_efficiency_score_no_data():
    """HR 데이터 없으면 5점."""
    assert _efficiency_score(None, 360, 150, 360) == 5.0


# ── calculate_weekly_score 통합 ─────────────────────────────────────────

def test_no_data(conn, test_config):
    """데이터 없을 때 오류 없이 반환."""
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    result = calculate_weekly_score(conn, monday.isoformat(), config=test_config)

    assert "total_score" in result
    assert "grade" in result
    assert "components" in result
    assert result["data"]["run_count"] == 0


def test_with_activity_data(conn, test_config):
    """활동 데이터 있을 때 총점 계산."""
    today = date.today()
    monday = today - timedelta(days=today.weekday())

    # 이번 주 활동 4개
    for i in range(4):
        d = monday + timedelta(days=i)
        _insert_activity(conn, "garmin", f"g{i}", f"{d.isoformat()}T08:00:00",
                         distance_km=10.0, avg_pace=360, avg_hr=150)

    result = calculate_weekly_score(conn, monday.isoformat(), config=test_config)
    assert result["total_score"] > 0
    assert result["grade"] in ("A", "B", "C", "D", "F")
    assert result["data"]["total_distance_km"] == pytest.approx(40.0)
    assert result["data"]["run_count"] == 4


def test_grade_boundaries(conn, test_config):
    """등급 경계값 테스트."""
    # 직접 점수 조합으로 등급 확인
    today = date.today()
    monday = today - timedelta(days=today.weekday())

    result = calculate_weekly_score(conn, monday.isoformat(), config=test_config)
    total = result["total_score"]
    grade = result["grade"]

    if total >= 85:
        assert grade == "A"
    elif total >= 70:
        assert grade == "B"
    elif total >= 55:
        assert grade == "C"
    elif total >= 40:
        assert grade == "D"
    else:
        assert grade == "F"


def test_components_sum_equals_total(conn, test_config):
    """컴포넌트 합계 = total_score."""
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    result = calculate_weekly_score(conn, monday.isoformat(), config=test_config)
    components_sum = sum(result["components"].values())
    assert components_sum == pytest.approx(result["total_score"], abs=0.01)


def test_dedup_in_weekly_score(conn, test_config):
    """matched_group_id 중복 제거 적용 확인."""
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    dt = f"{monday.isoformat()}T08:00:00"

    _insert_activity(conn, "garmin", "g1", dt, distance_km=10.0,
                     matched_group_id="grp1")
    _insert_activity(conn, "strava", "s1", dt, distance_km=10.1,
                     matched_group_id="grp1")

    result = calculate_weekly_score(conn, monday.isoformat(), config=test_config)
    assert result["data"]["run_count"] == 1


def test_config_target_used(conn):
    """config의 weekly_distance_target이 점수에 반영됨."""
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    _insert_activity(conn, "garmin", "g1", f"{monday.isoformat()}T08:00:00",
                     distance_km=40.0)

    config_50 = {"user": {"weekly_distance_target": 50.0}}
    config_40 = {"user": {"weekly_distance_target": 40.0}}

    r50 = calculate_weekly_score(conn, monday.isoformat(), config=config_50)
    r40 = calculate_weekly_score(conn, monday.isoformat(), config=config_40)

    # 40km 달성 시: 목표 40 → 100%, 목표 50 → 80% → 낮은 점수
    assert r40["components"]["volume"] >= r50["components"]["volume"]
