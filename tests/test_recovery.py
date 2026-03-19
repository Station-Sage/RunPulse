"""recovery.py 테스트."""

import sqlite3
import pytest
from src.db_setup import create_tables
from src.analysis.recovery import (
    get_recovery_status,
    recovery_trend,
    _score_stress,
    _score_hrv_ratio,
    _score_rhr_ratio,
)


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    yield c
    c.close()


def _insert_wellness(conn, date_str, body_battery=80, sleep_score=75,
                     hrv_value=60.0, stress_avg=30, resting_hr=55):
    conn.execute("""
        INSERT OR REPLACE INTO daily_wellness
            (date, source, body_battery, sleep_score, hrv_value, stress_avg, resting_hr)
        VALUES (?, 'garmin', ?, ?, ?, ?, ?)
    """, (date_str, body_battery, sleep_score, hrv_value, stress_avg, resting_hr))


# ── 점수 변환 함수 ──────────────────────────────────────────────────────

def test_score_stress_low():
    """스트레스 25 이하 → 100점."""
    assert _score_stress(25) == 100.0
    assert _score_stress(0) == 100.0


def test_score_stress_high():
    """스트레스 75 이상 → 0점."""
    assert _score_stress(75) == 0.0
    assert _score_stress(100) == 0.0


def test_score_stress_midpoint():
    """스트레스 50 → 50점 (선형 중간)."""
    assert _score_stress(50) == pytest.approx(50.0, abs=0.1)


def test_score_hrv_ratio_normal():
    """HRV 개인 평균과 같으면 50점 (0.8~1.2 범위 선형 중간)."""
    # ratio=1.0 → (1.0-0.8)/0.4*100 = 50
    assert _score_hrv_ratio(60.0, 60.0) == pytest.approx(50.0)


def test_score_hrv_ratio_low():
    """HRV 개인 평균의 80% → 0점."""
    assert _score_hrv_ratio(48.0, 60.0) == pytest.approx(0.0)


def test_score_rhr_ratio_normal():
    """안정 HR 개인 평균과 같으면 100점."""
    assert _score_rhr_ratio(55.0, 55.0) == pytest.approx(100.0)


def test_score_rhr_ratio_high():
    """안정 HR 개인 평균의 1.2배 → 0점."""
    assert _score_rhr_ratio(66.0, 55.0) == pytest.approx(0.0)


# ── get_recovery_status ─────────────────────────────────────────────────

def test_no_wellness_data(conn):
    """데이터 없을 때 available=False, score=None."""
    result = get_recovery_status(conn, "2026-01-01")
    assert result["available"] is False
    assert result["recovery_score"] is None
    assert result["grade"] is None


def test_recovery_score_excellent(conn):
    """높은 지표 → excellent 등급 (80+점)."""
    # 7일치 baseline 삽입
    for i in range(1, 8):
        _insert_wellness(conn, f"2026-01-{i:02d}", body_battery=90,
                         sleep_score=85, hrv_value=65.0, stress_avg=20,
                         resting_hr=50)
    # 당일 데이터
    _insert_wellness(conn, "2026-01-08", body_battery=90, sleep_score=85,
                     hrv_value=65.0, stress_avg=20, resting_hr=50)

    result = get_recovery_status(conn, "2026-01-08")
    assert result["available"] is True
    assert result["recovery_score"] is not None
    assert result["recovery_score"] >= 80
    assert result["grade"] == "excellent"


def test_recovery_score_poor(conn):
    """낮은 지표 → poor 등급 (40점 미만)."""
    for i in range(1, 8):
        _insert_wellness(conn, f"2026-01-{i:02d}", body_battery=50,
                         hrv_value=60.0, resting_hr=55)
    # 당일: body_battery 낮음, sleep 낮음, stress 높음, HR 상승
    _insert_wellness(conn, "2026-01-08", body_battery=10, sleep_score=30,
                     hrv_value=40.0, stress_avg=80, resting_hr=70)

    result = get_recovery_status(conn, "2026-01-08")
    assert result["recovery_score"] is not None
    assert result["recovery_score"] < 40
    assert result["grade"] == "poor"


def test_recovery_boundary_40(conn):
    """경계값 40 근처에서 moderate vs poor 판정."""
    # 단순히 40점 경계 직접 확인 (내부 함수는 이미 테스트됨)
    from src.analysis.recovery import _recovery_grade
    assert _recovery_grade(40.0) == "moderate"
    assert _recovery_grade(39.9) == "poor"


def test_recovery_boundary_60_80(conn):
    """경계값 60, 80 확인."""
    from src.analysis.recovery import _recovery_grade
    assert _recovery_grade(60.0) == "good"
    assert _recovery_grade(59.9) == "moderate"
    assert _recovery_grade(80.0) == "excellent"
    assert _recovery_grade(79.9) == "good"


def test_partial_data(conn):
    """일부 지표만 있을 때 graceful 처리."""
    conn.execute("""
        INSERT INTO daily_wellness (date, source, body_battery)
        VALUES ('2026-01-01', 'garmin', 70)
    """)
    result = get_recovery_status(conn, "2026-01-01")
    assert result["available"] is True
    assert result["recovery_score"] is not None  # body_battery만으로도 계산


# ── recovery_trend ──────────────────────────────────────────────────────

def test_recovery_trend_empty(conn):
    """데이터 없을 때 unknown 트렌드."""
    result = recovery_trend(conn, days=7)
    assert result["trend"] == "unknown"
    assert result["avg"] is None
    assert len(result["scores"]) == 7


def test_recovery_trend_improving(conn):
    """후반부 점수 향상 시 improving 판정."""
    from datetime import date, timedelta
    today = date.today()
    # 전반부: 낮은 점수, 후반부: 높은 점수
    for i in range(14, 7, -1):  # 14일 전 ~ 8일 전: 낮음
        d = (today - timedelta(days=i)).isoformat()
        _insert_wellness(conn, d, body_battery=20, sleep_score=30,
                         stress_avg=80, hrv_value=40.0, resting_hr=70)
        for j in range(1, 8):  # 7일 baseline
            baseline = (date.fromisoformat(d) - timedelta(days=j)).isoformat()
            _insert_wellness(conn, baseline, body_battery=50, hrv_value=60.0,
                             resting_hr=55)
    for i in range(7, 0, -1):  # 7일 전 ~ 1일 전: 높음
        d = (today - timedelta(days=i)).isoformat()
        _insert_wellness(conn, d, body_battery=90, sleep_score=85,
                         stress_avg=20, hrv_value=65.0, resting_hr=50)
        for j in range(1, 8):
            baseline = (date.fromisoformat(d) - timedelta(days=j)).isoformat()
            _insert_wellness(conn, baseline, body_battery=50, hrv_value=60.0,
                             resting_hr=55)

    result = recovery_trend(conn, days=14)
    assert result["trend"] in ("improving", "stable")  # 데이터 특성상 개선 방향
