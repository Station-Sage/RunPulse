"""Sprint 2 메트릭 단위 테스트.

TRIMP, ACWR, Monotony, UTRS, CIRS, Aerobic Decoupling, DI, DARP, RMR, engine.
"""
from __future__ import annotations

import math
import sqlite3

import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def conn():
    """인메모리 SQLite DB + Sprint 2에 필요한 최소 스키마."""
    c = sqlite3.connect(":memory:")
    c.execute(
        """CREATE TABLE activity_summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT,
            start_time TEXT,
            activity_type TEXT DEFAULT 'running',
            distance_km REAL,
            duration_sec INTEGER,
            avg_hr INTEGER,
            max_hr INTEGER,
            avg_pace_sec_km INTEGER,
            elevation_gain REAL,
            start_lat REAL,
            start_lon REAL
        )"""
    )
    c.execute(
        """CREATE TABLE activity_laps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            activity_id INTEGER NOT NULL,
            source TEXT NOT NULL,
            lap_index INTEGER NOT NULL,
            start_time TEXT,
            distance_km REAL,
            duration_sec INTEGER,
            avg_pace_sec_km INTEGER,
            avg_hr INTEGER,
            max_hr INTEGER,
            avg_cadence INTEGER,
            elevation_gain REAL,
            avg_power REAL
        )"""
    )
    c.execute(
        """CREATE TABLE computed_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            activity_id INTEGER,
            metric_name TEXT NOT NULL,
            metric_value REAL,
            metric_json TEXT,
            computed_at TEXT DEFAULT (datetime('now'))
        )"""
    )
    c.execute(
        """CREATE TABLE daily_wellness (
            date TEXT PRIMARY KEY,
            resting_hr INTEGER,
            sleep_score REAL,
            hrv_value REAL,
            body_battery REAL
        )"""
    )
    c.execute(
        """CREATE TABLE daily_fitness (
            date TEXT PRIMARY KEY,
            garmin_vo2max REAL,
            runalyze_evo2max REAL,
            runalyze_vdot REAL,
            tsb REAL
        )"""
    )
    c.execute(
        """CREATE TABLE activity_detail_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            activity_id INTEGER NOT NULL,
            metric_name TEXT NOT NULL,
            metric_value REAL
        )"""
    )
    # canonical view (simplified)
    c.execute(
        """CREATE VIEW v_canonical_activities AS
           SELECT id, source, start_time, activity_type,
                  distance_km, duration_sec, avg_hr, max_hr, avg_pace_sec_km
           FROM activity_summaries"""
    )
    c.commit()
    return c


# ---------------------------------------------------------------------------
# TRIMP
# ---------------------------------------------------------------------------


class TestTrimp:
    def test_basic_male(self):
        from src.metrics.trimp import calc_trimp

        t = calc_trimp(60.0, 150, 50, 185, gender="male")
        assert t is not None and t > 0

    def test_basic_female_lower(self):
        from src.metrics.trimp import calc_trimp

        male = calc_trimp(60.0, 150, 50, 185, gender="male")
        female = calc_trimp(60.0, 150, 50, 185, gender="female")
        # y 계수 남성(1.92) > 여성(1.67) → 동일 조건 남성 TRIMP > 여성
        assert male > female

    def test_zero_duration_returns_none(self):
        from src.metrics.trimp import calc_trimp

        assert calc_trimp(0.0, 150, 50, 185) is None

    def test_hr_below_rest_returns_none(self):
        from src.metrics.trimp import calc_trimp

        assert calc_trimp(60.0, 40, 50, 185) is None

    def test_hrss_calculation(self):
        from src.metrics.trimp import calc_hrss, calc_trimp

        trimp = calc_trimp(60.0, 155, 50, 185)
        hrss = calc_hrss(trimp, hr_lthr=161, hr_rest=50, hr_max=185)
        assert hrss is not None and hrss > 0

    def test_hrss_lthr_1hr_approx_100(self):
        """LTHR에서 1시간 = ~100점."""
        from src.metrics.trimp import calc_hrss, calc_trimp

        # LTHR = 185 * 0.87 ≈ 161
        trimp = calc_trimp(60.0, 161, 50, 185)
        hrss = calc_hrss(trimp, hr_lthr=161, hr_rest=50, hr_max=185)
        assert hrss is not None
        assert abs(hrss - 100.0) < 5.0  # 허용 오차 ±5

    def test_get_trimp_series_length(self, conn):
        from src.metrics.trimp import get_trimp_series

        series = get_trimp_series(conn, "2024-01-01", "2024-01-07")
        assert len(series) == 7

    def test_get_trimp_series_zeros_no_data(self, conn):
        from src.metrics.trimp import get_trimp_series

        series = get_trimp_series(conn, "2024-01-01", "2024-01-03")
        assert all(v == 0.0 for v in series)


# ---------------------------------------------------------------------------
# ACWR
# ---------------------------------------------------------------------------


class TestAcwr:
    def test_consistent_training_ratio(self):
        """일정 훈련 시 ACWR = acute_avg / chronic_avg = 80/80 = 1.0."""
        from src.metrics.acwr import calc_acwr

        trimp_7d = [80.0] * 7
        trimp_28d = [80.0] * 28
        acwr = calc_acwr(trimp_7d, trimp_28d)
        assert acwr is not None
        assert abs(acwr - 1.0) < 0.01

    def test_no_chronic_returns_none(self):
        from src.metrics.acwr import calc_acwr

        assert calc_acwr([100.0] * 7, [0.0] * 28) is None

    def test_danger_zone(self):
        from src.metrics.acwr import acwr_risk_level, calc_acwr

        trimp_7d = [200.0] * 7
        trimp_28d = [100.0] * 28
        acwr = calc_acwr(trimp_7d, trimp_28d)
        assert acwr is not None and acwr > 1.5
        assert acwr_risk_level(acwr) == "danger"

    def test_undertraining(self):
        from src.metrics.acwr import acwr_risk_level

        assert acwr_risk_level(0.5) == "undertraining"

    def test_caution_zone(self):
        from src.metrics.acwr import acwr_risk_level

        assert acwr_risk_level(1.4) == "caution"

    def test_acute_chronic_ratio(self):
        from src.metrics.acwr import calc_acwr

        # acute_avg = 700/7 = 100, chronic_avg = 1400/28 = 50 → ACWR = 2.0
        trimp_7d = [100.0] * 7
        trimp_28d = [50.0] * 28
        acwr = calc_acwr(trimp_7d, trimp_28d)
        assert acwr is not None
        assert abs(acwr - 2.0) < 0.1


# ---------------------------------------------------------------------------
# Monotony & Strain
# ---------------------------------------------------------------------------


class TestMonotony:
    def test_uniform_loads_returns_none(self):
        from src.metrics.monotony import calc_monotony

        # 완전히 동일 → std=0 → None
        assert calc_monotony([100.0] * 7) is None

    def test_varied_loads(self):
        from src.metrics.monotony import calc_monotony

        loads = [50.0, 100.0, 80.0, 120.0, 60.0, 90.0, 70.0]
        mono = calc_monotony(loads)
        assert mono is not None and mono > 0

    def test_insufficient_data_returns_none(self):
        from src.metrics.monotony import calc_monotony

        assert calc_monotony([100.0]) is None

    def test_strain_formula(self):
        from src.metrics.monotony import calc_monotony, calc_strain

        loads = [50.0, 100.0, 80.0, 120.0, 60.0, 90.0, 70.0]
        mono = calc_monotony(loads)
        strain = calc_strain(mono, loads)
        expected = mono * sum(loads)
        assert abs(strain - expected) < 0.001

    def test_high_monotony_flag(self):
        """매우 균일한 훈련 → 높은 monotony."""
        from src.metrics.monotony import calc_monotony

        # 약간의 변동 있어야 계산됨
        loads = [100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 101.0]
        mono = calc_monotony(loads)
        assert mono is not None and mono > 2.0


# ---------------------------------------------------------------------------
# UTRS
# ---------------------------------------------------------------------------


class TestUtrs:
    def test_all_optimal(self):
        from src.metrics.utrs import calc_utrs

        result = calc_utrs(
            sleep_score=90,
            hrv_score=90,
            tsb=10,
            resting_hr=50,
            sleep_start_times_min=[1380.0] * 7,  # 23:00 일정
        )
        assert result["utrs"] > 70

    def test_all_none_returns_neutral(self):
        from src.metrics.utrs import calc_utrs

        result = calc_utrs(None, None, None, None, None)
        # 모든 중립값 → utrs 계산 가능
        assert 0 < result["utrs"] < 100
        assert result["available_factors"] == []

    def test_sleep_factor_tracked(self):
        from src.metrics.utrs import calc_utrs

        result = calc_utrs(sleep_score=80, hrv_score=None, tsb=None, resting_hr=None, sleep_start_times_min=None)
        assert "sleep" in result["available_factors"]

    def test_tsb_normalization(self):
        from src.metrics.utrs import calc_utrs

        # tsb=25 (max) → tsb_norm = 100
        result = calc_utrs(None, None, tsb=25, resting_hr=None, sleep_start_times_min=None)
        assert result["tsb_norm"] == 100.0

    def test_tsb_min_normalization(self):
        from src.metrics.utrs import calc_utrs

        # tsb=-30 (min) → tsb_norm = 0
        result = calc_utrs(None, None, tsb=-30, resting_hr=None, sleep_start_times_min=None)
        assert result["tsb_norm"] == 0.0

    def test_grade_optimal(self):
        from src.metrics.utrs import utrs_grade

        assert utrs_grade(85) == "optimal"

    def test_grade_rest(self):
        from src.metrics.utrs import utrs_grade

        assert utrs_grade(30) == "rest"

    def test_sleep_consistency_varied_times(self):
        from src.metrics.utrs import calc_utrs

        # 취침 시각이 매우 불규칙
        times = [1200.0, 1440.0, 900.0, 1500.0, 800.0, 1380.0, 1320.0]
        result_varied = calc_utrs(None, None, None, None, times)
        # 일정한 시각
        times_consistent = [1380.0] * 7
        result_consistent = calc_utrs(None, None, None, None, times_consistent)
        assert result_consistent["consistency"] > result_varied["consistency"]


# ---------------------------------------------------------------------------
# CIRS
# ---------------------------------------------------------------------------


class TestCirs:
    def test_safe_zone(self):
        from src.metrics.cirs import calc_cirs, cirs_grade

        result = calc_cirs(acwr=1.0, monotony=1.2, lsi_weekly=1.0)
        assert result["cirs"] <= 20
        assert cirs_grade(result["cirs"]) == "safe"

    def test_danger_zone(self):
        from src.metrics.cirs import calc_cirs, cirs_grade

        result = calc_cirs(acwr=1.6, monotony=2.5, lsi_weekly=1.5)
        assert result["cirs"] > 50

    def test_no_asym_weight_normalization(self):
        """Asym 없으면 3요소 가중치 합=1이어야 함."""
        # 모든 risk=100이면 CIRS=100
        from src.metrics.cirs import calc_cirs

        result = calc_cirs(acwr=2.0, monotony=3.0, lsi_weekly=2.0, asym_pct=None)
        assert abs(result["cirs"] - 100.0) < 1.0

    def test_with_asym(self):
        from src.metrics.cirs import calc_cirs

        result = calc_cirs(acwr=2.0, monotony=3.0, lsi_weekly=2.0, asym_pct=10.0)
        assert result["has_asym_data"] is True
        assert result["asym_risk"] > 0

    def test_all_none_returns_zero(self):
        from src.metrics.cirs import calc_cirs

        result = calc_cirs(acwr=None, monotony=None, lsi_weekly=None)
        assert result["cirs"] == 0.0

    def test_grade_boundaries(self):
        from src.metrics.cirs import cirs_grade

        assert cirs_grade(10) == "safe"
        assert cirs_grade(35) == "caution"
        assert cirs_grade(65) == "warning"
        assert cirs_grade(90) == "danger"


# ---------------------------------------------------------------------------
# Aerobic Decoupling
# ---------------------------------------------------------------------------


class TestDecoupling:
    def test_no_drift(self):
        """페이스·HR 전/후반 동일 → 0% 분리."""
        from src.metrics.decoupling import calc_decoupling

        speeds1 = [200.0, 200.0, 200.0]
        hrs1 = [150.0, 150.0, 150.0]
        speeds2 = [200.0, 200.0, 200.0]
        hrs2 = [150.0, 150.0, 150.0]
        result = calc_decoupling(speeds1, hrs1, speeds2, hrs2)
        assert result is not None
        assert abs(result) < 0.01

    def test_positive_decoupling(self):
        """후반에 HR 증가 (페이스 동일) → 양의 분리."""
        from src.metrics.decoupling import calc_decoupling

        speeds1 = [200.0, 200.0, 200.0]
        hrs1 = [140.0, 140.0, 140.0]
        speeds2 = [200.0, 200.0, 200.0]
        hrs2 = [155.0, 155.0, 155.0]
        result = calc_decoupling(speeds1, hrs1, speeds2, hrs2)
        assert result is not None and result > 0

    def test_empty_input_returns_none(self):
        from src.metrics.decoupling import calc_decoupling

        assert calc_decoupling([], [], [200.0], [150.0]) is None

    def test_ef_calculation(self):
        from src.metrics.decoupling import calc_ef

        ef = calc_ef(200.0, 150.0)
        assert ef is not None
        assert abs(ef - 200.0 / 150.0) < 0.001

    def test_ef_zero_hr_returns_none(self):
        from src.metrics.decoupling import calc_ef

        assert calc_ef(200.0, 0.0) is None

    def test_grade_good(self):
        from src.metrics.decoupling import decoupling_grade

        assert decoupling_grade(3.0) == "good"

    def test_grade_moderate(self):
        from src.metrics.decoupling import decoupling_grade

        assert decoupling_grade(7.0) == "moderate"

    def test_grade_poor(self):
        from src.metrics.decoupling import decoupling_grade

        assert decoupling_grade(12.0) == "poor"

    def test_from_laps(self):
        from src.metrics.decoupling import calc_decoupling_from_laps

        laps = [
            {"avg_pace_sec_km": 300, "avg_hr": 140},
            {"avg_pace_sec_km": 300, "avg_hr": 140},
            {"avg_pace_sec_km": 300, "avg_hr": 155},
            {"avg_pace_sec_km": 300, "avg_hr": 155},
        ]
        result = calc_decoupling_from_laps(laps)
        assert result is not None and result > 0


# ---------------------------------------------------------------------------
# DI (Durability Index)
# ---------------------------------------------------------------------------


class TestDi:
    def test_no_drift_di_one(self):
        """전/후반 pace·HR 동일 → DI=1.0."""
        from src.metrics.di import calc_di_from_laps

        laps = [
            {"avg_pace_sec_km": 300, "avg_hr": 150},
            {"avg_pace_sec_km": 300, "avg_hr": 150},
            {"avg_pace_sec_km": 300, "avg_hr": 150},
            {"avg_pace_sec_km": 300, "avg_hr": 150},
        ]
        di = calc_di_from_laps(laps)
        assert di is not None
        assert abs(di - 1.0) < 0.01

    def test_pace_degradation_di_above_one(self):
        """후반 페이스 저하(sec/km 증가)·HR 동일 → pace_ratio > 1 → DI > 1."""
        from src.metrics.di import calc_di_from_laps

        laps = [
            {"avg_pace_sec_km": 300, "avg_hr": 150},
            {"avg_pace_sec_km": 300, "avg_hr": 150},
            {"avg_pace_sec_km": 330, "avg_hr": 150},  # 느려짐
            {"avg_pace_sec_km": 330, "avg_hr": 150},
        ]
        di = calc_di_from_laps(laps)
        # pace_ratio = 330/300 = 1.1, hr_ratio = 1.0 → DI = 1.1
        assert di is not None and di > 1.0

    def test_insufficient_laps_returns_none(self):
        from src.metrics.di import calc_di_from_laps

        assert calc_di_from_laps([{"avg_pace_sec_km": 300, "avg_hr": 150}]) is None

    def test_missing_hr_ignored(self):
        from src.metrics.di import calc_di_from_laps

        laps = [
            {"avg_pace_sec_km": 300, "avg_hr": None},
            {"avg_pace_sec_km": 300, "avg_hr": 150},
            {"avg_pace_sec_km": 300, "avg_hr": 150},
        ]
        # None HR 랩 제거 후 2개 남으면 계산 가능
        result = calc_di_from_laps(laps)
        assert result is not None

    def test_di_summary_average(self):
        from src.metrics.di import calc_di_summary

        values = [0.9, 1.0, 1.1]
        summary = calc_di_summary(values)
        assert abs(summary - 1.0) < 0.001

    def test_di_summary_excludes_zeros(self):
        from src.metrics.di import calc_di_summary

        assert calc_di_summary([0.0, 0.0]) == 0.0


# ---------------------------------------------------------------------------
# DARP
# ---------------------------------------------------------------------------


class TestDarp:
    def test_returns_all_distances(self):
        from src.metrics.darp import calc_darp

        for dist in ("5k", "10k", "half", "full"):
            result = calc_darp(vdot=50.0, distance_key=dist)
            assert result is not None
            assert result["pace_sec_km"] > 0
            assert result["time_sec"] > 0

    def test_5k_faster_than_marathon(self):
        """5K 페이스 < 마라톤 페이스."""
        from src.metrics.darp import calc_darp

        r5k = calc_darp(50.0, "5k")
        rfull = calc_darp(50.0, "full")
        assert r5k["pace_sec_km"] < rfull["pace_sec_km"]

    def test_di_penalty_half_only(self):
        """DI 낮으면 하프/풀에만 페널티. 5K는 영향 없음."""
        from src.metrics.darp import calc_darp

        r5k_no = calc_darp(50.0, "5k")
        r5k_di = calc_darp(50.0, "5k", di=30)  # DI 30/100
        assert r5k_no["pace_sec_km"] == r5k_di["pace_sec_km"]

        rhalf_no = calc_darp(50.0, "half")
        rhalf_di = calc_darp(50.0, "half", di=30)
        assert rhalf_di["pace_sec_km"] > rhalf_no["pace_sec_km"]

    def test_invalid_vdot_returns_none(self):
        from src.metrics.darp import calc_darp
        assert calc_darp(0.0, "5k") is None
        assert calc_darp(-10.0, "full") is None

    def test_unknown_distance_returns_none(self):
        from src.metrics.darp import calc_darp
        assert calc_darp(50.0, "marathon") is None

    def test_di_high_no_penalty(self):
        """DI 70+ → 페널티 없음."""
        from src.metrics.darp import calc_darp

        rhalf_base = calc_darp(50.0, "half")
        rhalf_di_high = calc_darp(50.0, "half", di=80)
        assert rhalf_base["pace_sec_km"] == rhalf_di_high["pace_sec_km"]

    def test_shape_penalty(self):
        """Race Shape 낮으면 시간 추가."""
        from src.metrics.darp import calc_darp

        r_good = calc_darp(50.0, "full", race_shape=90)
        r_bad = calc_darp(50.0, "full", race_shape=30)
        assert r_bad["time_sec"] > r_good["time_sec"]

    def test_daniels_table_accuracy(self):
        """VDOT 50 → 마라톤 예측 ~3:10 (11440초) 근처."""
        from src.metrics.darp import calc_darp

        r = calc_darp(50.0, "full")
        assert 11000 < r["base_time_sec"] < 12000

    def test_time_sec_equals_pace_times_distance(self):
        from src.metrics.darp import calc_darp

        result = calc_darp(50.0, "10k")
        expected = result["pace_sec_km"] * 10.0
        assert abs(result["time_sec"] - expected) <= 1  # 반올림 허용


# ---------------------------------------------------------------------------
# RMR
# ---------------------------------------------------------------------------


class TestRmr:
    def test_all_data_returns_five_axes(self):
        from src.metrics.rmr import calc_rmr

        result = calc_rmr(
            vo2max=55.0,
            hr_lthr=160.0,
            hr_max=185.0,
            di=1.0,
            avg_cadence=178.0,
            vertical_ratio_pct=7.0,
            body_battery=80.0,
            sleep_score=75.0,
        )
        assert set(result["axes"].keys()) == {"유산소용량", "역치강도", "지구력", "동작효율성", "회복력"}

    def test_all_none_uses_neutral(self):
        from src.metrics.rmr import calc_rmr

        result = calc_rmr(None, None, None, None, None, None, None, None)
        assert result["overall"] == 50.0
        assert result["available"] == []

    def test_optimal_cadence_100(self):
        """178spm → cadence_score 100."""
        from src.metrics.rmr import calc_rmr

        result = calc_rmr(None, None, None, None, avg_cadence=178.0, vertical_ratio_pct=None, body_battery=None, sleep_score=None)
        # 케이던스만 available
        assert "케이던스" in result["available"]

    def test_poor_cadence_deducted(self):
        """160spm (178-18 = 18spm 이탈 × 3 = 54점 감점)."""
        from src.metrics.rmr import calc_rmr

        result = calc_rmr(None, None, None, None, avg_cadence=160.0, vertical_ratio_pct=None, body_battery=None, sleep_score=None)
        # cadence_score = max(0, 100 - 18*3) = 46
        # movement = (46 + 50) / 2 = 48 (vr neutral=50)
        assert result["axes"]["동작효율성"] == 48.0

    def test_vr_optimal_range_100(self):
        """VR 7% (6~8% 최적) → vr_score 100."""
        from src.metrics.rmr import calc_rmr

        result = calc_rmr(None, None, None, None, avg_cadence=None, vertical_ratio_pct=7.0, body_battery=None, sleep_score=None)
        assert "수직진동비" in result["available"]

    def test_aerobic_capacity_clamp(self):
        """VO2max=65 → 100점."""
        from src.metrics.rmr import calc_rmr

        result = calc_rmr(vo2max=65.0, hr_lthr=None, hr_max=None, di=None, avg_cadence=None, vertical_ratio_pct=None, body_battery=None, sleep_score=None)
        assert result["axes"]["유산소용량"] == 100.0

    def test_overall_is_average_of_axes(self):
        from src.metrics.rmr import calc_rmr

        result = calc_rmr(
            vo2max=45.0, hr_lthr=155.0, hr_max=185.0, di=0.9,
            avg_cadence=175.0, vertical_ratio_pct=8.5, body_battery=60.0, sleep_score=70.0,
        )
        expected = sum(result["axes"].values()) / 5.0
        assert abs(result["overall"] - expected) < 0.1


# ---------------------------------------------------------------------------
# Engine (smoke test with in-memory DB)
# ---------------------------------------------------------------------------


class TestEngine:
    def test_run_for_date_no_activities(self, conn):
        """활동 없는 날짜 — 오류 없이 빈 결과 반환."""
        from src.metrics.engine import run_for_date

        result = run_for_date(conn, "2024-06-01")
        assert "activity_metrics" in result
        assert "daily" in result
        assert result["activity_metrics"] == {}

    def test_run_daily_metrics_runs_without_error(self, conn):
        """활동·wellness 데이터 없어도 daily 메트릭 오류 없이 실행."""
        from src.metrics.engine import run_daily_metrics

        result = run_daily_metrics(conn, "2024-06-01")
        assert isinstance(result, dict)

    def test_run_weekly_metrics_no_vdot(self, conn):
        """VDOT 없으면 MarathonShape=None — 오류 없이 빈 결과."""
        from src.metrics.engine import run_weekly_metrics

        result = run_weekly_metrics(conn, "2024-06-01")
        assert "MarathonShape" not in result  # VDOT 없으면 계산 안 됨

    def test_recompute_all_short_range(self, conn):
        """3일 범위 recompute — 오류 없이 3개 날짜 반환."""
        from src.metrics.engine import run_for_date_range

        results = run_for_date_range(conn, "2024-06-01", "2024-06-03")
        assert len(results) == 3
        assert "2024-06-01" in results
        assert "2024-06-03" in results
