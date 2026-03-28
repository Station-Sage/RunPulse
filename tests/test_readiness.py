"""src/training/readiness.py 단위 테스트."""
from __future__ import annotations

import sqlite3
import pytest

from src.training.readiness import (
    _vdot_from_race,
    vdot_to_time,
    get_taper_weeks,
    get_recommended_weeks,
    get_phase_for_week,
    recommend_weekly_km,
    analyze_readiness,
)


# ── VDOT 공식 ────────────────────────────────────────────────────────────

class TestVdotFormulas:
    def test_vdot_from_5k_known(self):
        """5K 20분 → VDOT ≈ 47.5 (Daniels 표 참조)."""
        v = _vdot_from_race(5000, 20 * 60)
        assert v is not None
        assert 45.0 <= v <= 50.0

    def test_vdot_from_marathon_known(self):
        """마라톤 3:30 → VDOT ≈ 47 (Daniels 표 참조)."""
        v = _vdot_from_race(42195, 210 * 60)
        assert v is not None
        assert 44.0 <= v <= 50.0

    def test_vdot_from_race_invalid(self):
        assert _vdot_from_race(0, 1200) is None
        assert _vdot_from_race(5000, 0) is None
        assert _vdot_from_race(-1, 1200) is None

    def test_vdot_to_time_roundtrip(self):
        """VDOT → 시간 → VDOT 역산 왕복 일치."""
        original_vdot = 45.0
        t = vdot_to_time(original_vdot, 5000)
        assert t is not None
        recovered = _vdot_from_race(5000, t)
        assert recovered is not None
        assert abs(recovered - original_vdot) < 0.5

    def test_vdot_to_time_invalid(self):
        assert vdot_to_time(0, 5000) is None
        assert vdot_to_time(45, 0) is None

    def test_vdot_to_time_higher_vdot_faster(self):
        """VDOT가 높을수록 예상 시간이 짧아야 한다."""
        t40 = vdot_to_time(40.0, 10000)
        t55 = vdot_to_time(55.0, 10000)
        assert t40 is not None and t55 is not None
        assert t55 < t40


# ── 거리별 규칙 ──────────────────────────────────────────────────────────

class TestDistanceRules:
    def test_taper_5k(self):
        assert get_taper_weeks(5.0) == 1

    def test_taper_10k(self):
        assert get_taper_weeks(10.0) == 1

    def test_taper_half(self):
        assert get_taper_weeks(21.1) == 2

    def test_taper_full(self):
        assert get_taper_weeks(42.2) == 3

    def test_recommended_5k(self):
        rec = get_recommended_weeks(5.0)
        assert rec["min"] == 6
        assert rec["optimal_min"] == 8
        assert rec["taper"] == 1

    def test_recommended_full(self):
        rec = get_recommended_weeks(42.2)
        assert rec["min"] == 16
        assert rec["taper"] == 3

    def test_recommended_half(self):
        rec = get_recommended_weeks(21.1)
        assert rec["min"] == 12
        assert rec["taper"] == 2


# ── 훈련 단계 ────────────────────────────────────────────────────────────

class TestPhaseForWeek:
    def test_last_week_is_taper(self):
        phase = get_phase_for_week(13, 14, 2)
        assert phase == "taper"

    def test_second_to_last_is_taper_too(self):
        phase = get_phase_for_week(12, 14, 2)
        assert phase == "taper"

    def test_first_week_is_base(self):
        phase = get_phase_for_week(0, 16, 3)
        assert phase == "base"

    def test_mid_week_is_build(self):
        # 16주 플랜, 테이퍼 3주: training=13주, base=0~5, build=5~10, peak=10~13
        phase = get_phase_for_week(7, 16, 3)
        assert phase == "build"

    def test_late_week_is_peak(self):
        phase = get_phase_for_week(11, 16, 3)
        assert phase == "peak"


# ── 주간 km 추천 ─────────────────────────────────────────────────────────

class TestRecommendWeeklyKm:
    def test_base_lower_than_build(self):
        base_km = recommend_weekly_km(45, "10k", "base", 0, 12)
        build_km = recommend_weekly_km(45, "10k", "build", 4, 12)
        assert base_km < build_km

    def test_taper_lowest(self):
        taper_km = recommend_weekly_km(45, "half", "taper", 14, 16)
        build_km = recommend_weekly_km(45, "half", "build", 8, 16)
        assert taper_km < build_km

    def test_recovery_week_lower(self):
        """week_index % 4 == 3 이면 20% 감소."""
        normal_km = recommend_weekly_km(45, "10k", "build", 4, 12)  # cycle_pos=0
        recovery_km = recommend_weekly_km(45, "10k", "build", 7, 12)  # cycle_pos=3
        assert recovery_km < normal_km

    def test_higher_vdot_higher_km(self):
        low_km  = recommend_weekly_km(30, "full", "build", 4, 20)
        high_km = recommend_weekly_km(58, "full", "build", 4, 20)
        assert high_km > low_km

    def test_returns_positive(self):
        km = recommend_weekly_km(40, "5k", "base", 0, 10)
        assert km > 0


# ── analyze_readiness (통합) ─────────────────────────────────────────────

@pytest.fixture
def empty_conn():
    """빈 인메모리 DB (computed_metrics 테이블만 생성)."""
    conn = sqlite3.connect(":memory:")
    conn.execute("""
        CREATE TABLE computed_metrics (
            id INTEGER PRIMARY KEY,
            date TEXT,
            metric_name TEXT,
            metric_value REAL,
            metric_json TEXT,
            activity_id INTEGER
        )
    """)
    return conn


@pytest.fixture
def populated_conn(empty_conn):
    """VDOT_ADJ=45, DI=60, RTTI=85 데이터가 있는 DB."""
    today = "2026-03-28"
    rows = [
        (today, "VDOT_ADJ", 45.0),
        (today, "DI",       60.0),
        (today, "RTTI",     85.0),
    ]
    empty_conn.executemany(
        "INSERT INTO computed_metrics (date, metric_name, metric_value)"
        " VALUES (?, ?, ?)",
        rows,
    )
    return empty_conn


class TestAnalyzeReadiness:
    def test_no_vdot_returns_zero_pct(self, empty_conn):
        result = analyze_readiness(empty_conn, 10.0, 3600, 12)
        assert result["achievability_pct"] == 0.0
        assert result["current_vdot"] is None
        assert any("VDOT" in w for w in result["warnings"])

    def test_easy_goal_high_pct(self, populated_conn):
        """현재 VDOT 45, 목표 5K 30분(매우 쉬운 목표) → 달성률 100%."""
        result = analyze_readiness(populated_conn, 5.0, 30 * 60, 10)
        assert result["achievability_pct"] == 100.0
        assert result["vdot_gap"] is not None
        assert result["vdot_gap"] <= 0

    def test_hard_goal_lower_pct(self, populated_conn):
        """VDOT 45, 마라톤 2:50 목표(VDOT~58, gap=13) → 중급자 16주 달성률 < 80%."""
        result = analyze_readiness(populated_conn, 42.195, 170 * 60, 16)
        # VDOT 45 중급자: VO2max+RE+LT 합산 16주 ~3 VDOT 향상 → 달성 도전적
        assert result["achievability_pct"] < 80.0

    def test_moderate_goal_reasonable_pct(self, populated_conn):
        """VDOT 45, 5K 21분 목표(VDOT~46) → 달성 가능, 높은 달성률."""
        result = analyze_readiness(populated_conn, 5.0, 21 * 60, 10)
        assert result["achievability_pct"] > 70.0
        assert result["vdot_gap"] is not None
        assert result["vdot_gap"] > 0

    def test_below_min_weeks_capped(self, populated_conn):
        """최솟값(12주) 미만 기간 선택 시 달성률 70% 상한."""
        result = analyze_readiness(populated_conn, 21.097, 90 * 60, 8)
        assert result["achievability_pct"] <= 70.0
        assert any("짧습니다" in w for w in result["warnings"])

    def test_recommended_weeks_structure(self, populated_conn):
        result = analyze_readiness(populated_conn, 10.0, 3600, 12)
        rec = result["recommended_weeks"]
        assert "min" in rec
        assert "optimal_min" in rec
        assert "optimal_max" in rec
        assert "taper" in rec

    def test_projected_times_make_sense(self, populated_conn):
        """훈련 후 예상 기록이 현재 예상 기록보다 빠르거나 같아야."""
        result = analyze_readiness(populated_conn, 10.0, 3000, 12)
        now_t = result["projected_time_now"]
        end_t = result["projected_time_end"]
        if now_t and end_t:
            assert end_t <= now_t

    def test_status_summary_not_empty(self, populated_conn):
        result = analyze_readiness(populated_conn, 10.0, 3000, 12)
        assert len(result["status_summary"]) > 0

    def test_weekly_vdot_gain_positive(self, populated_conn):
        result = analyze_readiness(populated_conn, 10.0, 3000, 12)
        assert result["weekly_vdot_gain"] > 0
