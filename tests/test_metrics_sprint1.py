"""Sprint 1 메트릭 단위 테스트: GAP, LSI, FEARP, ADTI, TIDS, Relative Effort, Marathon Shape."""
from __future__ import annotations

import json
import sqlite3

import pytest


@pytest.fixture
def mem_conn():
    """인메모리 SQLite + 전체 스키마."""
    from src.db_setup import create_tables, migrate_db
    conn = sqlite3.connect(":memory:")
    create_tables(conn)
    migrate_db(conn)
    yield conn
    conn.close()


def _insert_activity(conn, source_id, start_time, distance_km=10.0,
                     duration_sec=3600, avg_pace=360, avg_hr=150, max_hr=180,
                     elevation_gain=None, start_lat=None, start_lon=None):
    conn.execute(
        """INSERT INTO activity_summaries
           (source, source_id, start_time, activity_type, distance_km,
            duration_sec, avg_pace_sec_km, avg_hr, max_hr, elevation_gain,
            start_lat, start_lon)
           VALUES ('garmin',?,?,'running',?,?,?,?,?,?,?,?)""",
        (source_id, start_time, distance_km, duration_sec, avg_pace,
         avg_hr, max_hr, elevation_gain, start_lat, start_lon),
    )
    return conn.execute(
        "SELECT id FROM activity_summaries WHERE source_id=?", (source_id,)
    ).fetchone()[0]


# ─────────────────────────────────────────────────────────────
# GAP / NGP
# ─────────────────────────────────────────────────────────────

class TestGAP:
    def test_flat_grade_no_adjustment(self):
        """평지(grade=0)에서 GAP = actual_pace."""
        from src.metrics.gap import calc_gap
        assert calc_gap(300.0, 0.0) == pytest.approx(300.0, rel=1e-6)

    def test_uphill_gap_lower_than_actual(self):
        """오르막에서 GAP < actual_pace (평지 등가가 더 빠름)."""
        from src.metrics.gap import calc_gap
        gap = calc_gap(360.0, 10.0)  # 10% 오르막
        assert gap < 360.0

    def test_downhill_capped_at_minus10(self):
        """-15% 내리막은 -10%로 cap."""
        from src.metrics.gap import calc_gap
        gap_minus10 = calc_gap(300.0, -10.0)
        gap_minus15 = calc_gap(300.0, -15.0)
        assert gap_minus10 == pytest.approx(gap_minus15, rel=1e-6)

    def test_effort_factor_uphill(self):
        """오르막 5% → effort_factor > 1."""
        from src.metrics.gap import calc_gap_effort_factor
        ef = calc_gap_effort_factor(5.0)
        assert ef > 1.0

    def test_ngp_single_segment(self):
        """단일 구간 NGP ≈ GAP (평지)."""
        from src.metrics.gap import calc_ngp_from_laps, pace_to_speed, speed_to_pace
        speed = pace_to_speed(300.0)  # 300초/km → m/min
        ngp_speed = calc_ngp_from_laps([speed], [0.0], [1800.0])
        ngp_pace = speed_to_pace(ngp_speed)
        assert ngp_pace == pytest.approx(300.0, rel=1e-3)

    def test_ngp_returns_none_empty(self):
        """빈 리스트이면 None 반환."""
        from src.metrics.gap import calc_ngp_from_laps
        assert calc_ngp_from_laps([], [], []) is None

    def test_pace_speed_roundtrip(self):
        """pace → speed → pace 변환 정합성."""
        from src.metrics.gap import pace_to_speed, speed_to_pace
        original = 300.0
        assert speed_to_pace(pace_to_speed(original)) == pytest.approx(original, rel=1e-6)


# ─────────────────────────────────────────────────────────────
# LSI
# ─────────────────────────────────────────────────────────────

class TestLSI:
    def test_normal_range(self):
        """21일 평균과 동일 부하 → LSI = 1.0."""
        from src.metrics.lsi import calc_lsi
        lsi = calc_lsi(10.0, [10.0] * 21)
        assert lsi == pytest.approx(1.0)

    def test_spike_danger(self):
        """오늘 부하 = 21일 평균의 2배 → LSI = 2.0."""
        from src.metrics.lsi import calc_lsi
        lsi = calc_lsi(20.0, [10.0] * 21)
        assert lsi == pytest.approx(2.0)

    def test_no_load_today(self):
        """오늘 부하 0 → None."""
        from src.metrics.lsi import calc_lsi
        assert calc_lsi(0.0, [10.0] * 21) is None

    def test_no_rolling_data(self):
        """과거 부하 없음 → None."""
        from src.metrics.lsi import calc_lsi
        assert calc_lsi(10.0, []) is None

    def test_risk_levels(self):
        """위험 수준 분류 정확성."""
        from src.metrics.lsi import lsi_risk_level
        assert lsi_risk_level(0.5) == "low"
        assert lsi_risk_level(1.0) == "normal"
        assert lsi_risk_level(1.4) == "caution"
        assert lsi_risk_level(1.6) == "danger"

    def test_calc_and_save(self, mem_conn):
        """calc_and_save_lsi DB 연동."""
        from src.metrics.lsi import calc_and_save_lsi
        # 활동 삽입 (오늘 = 2026-03-23)
        _insert_activity(mem_conn, "g1", "2026-03-23T07:00:00", distance_km=12.0)
        # 과거 21일 활동 삽입
        for i in range(1, 22):
            _insert_activity(mem_conn, f"g_old_{i}", f"2026-03-{22-i:02d}T07:00:00", distance_km=10.0)
        result = calc_and_save_lsi(mem_conn, "2026-03-23")
        assert result is not None
        assert result > 0


# ─────────────────────────────────────────────────────────────
# FEARP
# ─────────────────────────────────────────────────────────────

class TestFEARP:
    def test_standard_conditions_no_change(self):
        """표준 조건(15°C, 50%, 평지, 0m) → FEARP = actual_pace."""
        from src.metrics.fearp import calc_fearp
        result = calc_fearp(300.0, grade_pct=0.0, temp_c=15.0, humidity_pct=50.0, altitude_m=0.0)
        assert result == pytest.approx(300.0, rel=1e-4)

    def test_hot_weather_lower_fearp(self):
        """더운 날씨(30°C) → FEARP < actual_pace (등가 페이스가 실제보다 빠름)."""
        from src.metrics.fearp import calc_fearp
        fearp_hot = calc_fearp(300.0, temp_c=30.0)
        assert fearp_hot < 300.0

    def test_humid_conditions(self):
        """고습도(90%) → FEARP < actual_pace."""
        from src.metrics.fearp import calc_fearp
        fearp_humid = calc_fearp(300.0, humidity_pct=90.0)
        assert fearp_humid < 300.0

    def test_uphill_lower_fearp(self):
        """오르막(5%) → FEARP < actual_pace (평지 등가가 더 빠름)."""
        from src.metrics.fearp import calc_fearp
        fearp_uphill = calc_fearp(360.0, grade_pct=5.0)
        assert fearp_uphill < 360.0

    def test_breakdown_keys(self):
        """fearp_breakdown 결과에 필수 키 포함."""
        from src.metrics.fearp import fearp_breakdown
        result = fearp_breakdown(300.0, temp_c=20.0, humidity_pct=60.0)
        for key in ("fearp", "actual_pace", "temp_factor", "humidity_factor", "altitude_factor", "grade_factor"):
            assert key in result

    def test_calc_and_save_no_weather(self, mem_conn):
        """날씨 없어도 FEARP 계산 (fallback: 표준 조건)."""
        from unittest.mock import patch
        from src.metrics.fearp import calc_and_save_fearp
        act_id = _insert_activity(
            mem_conn, "g1", "2026-03-23T07:00:00",
            distance_km=10.0, avg_pace=360, elevation_gain=50.0,
        )
        with patch("src.metrics.fearp.get_weather_for_activity", return_value=None):
            result = calc_and_save_fearp(mem_conn, act_id)
        assert result is not None


# ─────────────────────────────────────────────────────────────
# ADTI
# ─────────────────────────────────────────────────────────────

class TestADTI:
    def test_improving_trend(self):
        """감소 추세 → 음수 기울기 (개선)."""
        from src.metrics.adti import calc_adti
        adti = calc_adti([10.0, 8.0, 6.0, 4.0, 2.0])
        assert adti is not None
        assert adti < 0

    def test_worsening_trend(self):
        """증가 추세 → 양수 기울기 (악화)."""
        from src.metrics.adti import calc_adti
        adti = calc_adti([2.0, 4.0, 6.0, 8.0, 10.0])
        assert adti is not None
        assert adti > 0

    def test_flat_trend(self):
        """동일 값 → 기울기 = 0."""
        from src.metrics.adti import calc_adti
        adti = calc_adti([5.0, 5.0, 5.0, 5.0])
        assert adti == pytest.approx(0.0)

    def test_insufficient_data(self):
        """데이터 2개 미만 → None."""
        from src.metrics.adti import calc_adti
        assert calc_adti([5.0, 4.0]) is None
        assert calc_adti([]) is None

    def test_status_labels(self):
        """상태 레이블 정확성."""
        from src.metrics.adti import adti_status
        assert adti_status(-1.0) == "improving"
        assert adti_status(-0.2) == "stable"
        assert adti_status(0.5) == "declining"

    def test_calc_and_save_no_data(self, mem_conn):
        """Decoupling 데이터 없으면 None 반환."""
        from src.metrics.adti import calc_and_save_adti
        result = calc_and_save_adti(mem_conn, "2026-03-23")
        assert result is None


# ─────────────────────────────────────────────────────────────
# TIDS
# ─────────────────────────────────────────────────────────────

class TestTIDS:
    def test_polarized_distribution(self):
        """폴라리제드 분포(80/5/15) → polar_dev=0."""
        from src.metrics.tids import calc_tids
        # 80분 z1-2, 5분 z3, 15분 z4-5 (임의 분할)
        result = calc_tids([70.0, 10.0, 5.0, 10.0, 5.0])
        assert result["polar_dev"] == pytest.approx(0.0, abs=0.5)

    def test_dominant_model_polarized(self):
        """폴라리제드 분포 → dominant='polarized'."""
        from src.metrics.tids import calc_tids
        result = calc_tids([70.0, 10.0, 5.0, 10.0, 5.0])
        assert result["dominant_model"] == "polarized"

    def test_all_zone3(self):
        """전부 Zone3이면 pyramid_dev, polar_dev 큼."""
        from src.metrics.tids import calc_tids
        result = calc_tids([0.0, 0.0, 100.0, 0.0, 0.0])
        assert result["z3"] == pytest.approx(100.0)
        assert result["polar_dev"] > 50

    def test_empty_zones(self):
        """빈 데이터 → z12=z3=z45=0, dominant=None."""
        from src.metrics.tids import calc_tids
        result = calc_tids([0.0] * 5)
        assert result["dominant_model"] is None

    def test_result_keys(self):
        """결과 딕셔너리에 필수 키 포함."""
        from src.metrics.tids import calc_tids
        result = calc_tids([40.0, 20.0, 15.0, 15.0, 10.0])
        for key in ("z12", "z3", "z45", "polar_dev", "pyramid_dev", "health_dev", "dominant_model"):
            assert key in result

    def test_percentages_sum_100(self):
        """z12 + z3 + z45 = 100 (데이터 있을 때)."""
        from src.metrics.tids import calc_tids
        result = calc_tids([40.0, 20.0, 15.0, 15.0, 10.0])
        total = result["z12"] + result["z3"] + result["z45"]
        assert total == pytest.approx(100.0, abs=0.2)

    def test_calc_and_save_no_data(self, mem_conn):
        """HR존 데이터 없으면 None 반환."""
        from src.metrics.tids import calc_and_save_tids
        result = calc_and_save_tids(mem_conn, "2026-03-23")
        assert result is None

    def test_calc_and_save_with_zone_data(self, mem_conn):
        """HR존 데이터 있으면 계산 후 저장."""
        from src.metrics.tids import calc_and_save_tids
        act_id = _insert_activity(mem_conn, "g1", "2026-03-20T07:00:00")
        # hr_zone_time 삽입 (초 단위)
        for i in range(1, 6):
            mem_conn.execute(
                """INSERT INTO activity_detail_metrics
                   (activity_id, source, metric_name, metric_value)
                   VALUES (?,?,?,?)""",
                (act_id, "garmin", f"hr_zone_time_{i}", [1800, 1200, 300, 600, 300][i-1]),
            )
        result = calc_and_save_tids(mem_conn, "2026-03-23")
        assert result is not None
        assert result["dominant_model"] is not None


# ─────────────────────────────────────────────────────────────
# Relative Effort
# ─────────────────────────────────────────────────────────────

class TestRelativeEffort:
    def test_pure_zone1(self):
        """60분 Zone1만 → RE = 60 * 0.5 = 30."""
        from src.metrics.relative_effort import calc_relative_effort
        re = calc_relative_effort([3600.0, 0.0, 0.0, 0.0, 0.0])
        assert re == pytest.approx(30.0)

    def test_pure_zone5(self):
        """60분 Zone5만 → RE = 60 * 5.5 = 330."""
        from src.metrics.relative_effort import calc_relative_effort
        re = calc_relative_effort([0.0, 0.0, 0.0, 0.0, 3600.0])
        assert re == pytest.approx(330.0)

    def test_mixed_zones(self):
        """복합 존 RE 계산."""
        from src.metrics.relative_effort import calc_relative_effort
        # 30분 z1 + 20분 z3 + 10분 z5
        re = calc_relative_effort([1800.0, 0.0, 1200.0, 0.0, 600.0])
        expected = 30 * 0.5 + 20 * 2.0 + 10 * 5.5
        assert re == pytest.approx(expected)

    def test_empty_zones(self):
        """모두 0이면 RE = 0."""
        from src.metrics.relative_effort import calc_relative_effort
        assert calc_relative_effort([0.0] * 5) == pytest.approx(0.0)

    def test_calc_and_save_with_zone_data(self, mem_conn):
        """HR존 데이터 있으면 RE 계산 후 저장."""
        from src.metrics.relative_effort import calc_and_save_relative_effort
        act_id = _insert_activity(mem_conn, "g1", "2026-03-23T07:00:00")
        for i in range(1, 6):
            mem_conn.execute(
                """INSERT INTO activity_detail_metrics
                   (activity_id, source, metric_name, metric_value)
                   VALUES (?,?,?,?)""",
                (act_id, "garmin", f"hr_zone_time_{i}", [1800, 1200, 300, 600, 300][i-1]),
            )
        result = calc_and_save_relative_effort(mem_conn, act_id)
        assert result is not None
        assert result > 0

    def test_calc_and_save_fallback_avg_hr(self, mem_conn):
        """HR존 데이터 없으면 avg_hr 기반 근사."""
        from src.metrics.relative_effort import calc_and_save_relative_effort
        act_id = _insert_activity(
            mem_conn, "g2", "2026-03-23T08:00:00",
            avg_hr=155, max_hr=185, duration_sec=3600,
        )
        result = calc_and_save_relative_effort(mem_conn, act_id)
        assert result is not None
        assert result > 0


# ─────────────────────────────────────────────────────────────
# Marathon Shape
# ─────────────────────────────────────────────────────────────

class TestMarathonShape:
    def test_optimal_training(self):
        """VDOT 50: 충분한 주간 볼륨 + 장거리런 → shape 90%+."""
        from src.metrics.marathon_shape import calc_marathon_shape
        # VDOT 50 → target_weekly=65km, target_long=27.5km
        shape = calc_marathon_shape(
            weekly_km_avg=70.0,   # 목표 초과
            longest_run_km=30.0,  # 목표 초과
            vdot=50.0,
        )
        assert shape is not None
        assert shape >= 90.0

    def test_partial_training(self):
        """주간 거리 절반 → shape < 80% (볼륨 부족)."""
        from src.metrics.marathon_shape import calc_marathon_shape
        shape = calc_marathon_shape(
            weekly_km_avg=30.0,   # 65km 목표 대비 46%
            longest_run_km=27.5,  # 목표 달성
            vdot=50.0,
        )
        assert shape is not None
        assert shape < 80.0

    def test_no_vdot(self):
        """VDOT 없으면 None."""
        from src.metrics.marathon_shape import calc_marathon_shape
        assert calc_marathon_shape(40.0, 20.0, 0.0) is None
        assert calc_marathon_shape(40.0, 20.0, None) is None

    def test_label_mapping(self):
        """레이블 경계 값 확인."""
        from src.metrics.marathon_shape import marathon_shape_label
        assert marathon_shape_label(30.0) == "insufficient"
        assert marathon_shape_label(50.0) == "base"
        assert marathon_shape_label(70.0) == "building"
        assert marathon_shape_label(85.0) == "ready"
        assert marathon_shape_label(95.0) == "peak"

    def test_calc_and_save_no_vdot(self, mem_conn):
        """VDOT 없으면 None 반환."""
        from src.metrics.marathon_shape import calc_and_save_marathon_shape
        result = calc_and_save_marathon_shape(mem_conn, "2026-03-23")
        assert result is None

    def test_calc_and_save_with_vdot(self, mem_conn):
        """VDOT + 활동 데이터 있으면 계산 후 저장."""
        from src.metrics.marathon_shape import calc_and_save_marathon_shape
        # VDOT 삽입
        mem_conn.execute(
            """INSERT INTO daily_fitness (date, source, runalyze_vdot)
               VALUES ('2026-03-20', 'runalyze', 48.0)"""
        )
        # 최근 4주 활동 삽입
        for i in range(4):
            _insert_activity(
                mem_conn, f"g{i}", f"2026-03-{20-i*7:02d}T07:00:00",
                distance_km=15.0,
            )
        _insert_activity(mem_conn, "long1", "2026-03-15T07:00:00", distance_km=22.0)

        result = calc_and_save_marathon_shape(mem_conn, "2026-03-23")
        assert result is not None
        assert 0 <= result <= 100


# ─────────────────────────────────────────────────────────────
# Store helpers
# ─────────────────────────────────────────────────────────────

class TestMetricStore:
    def test_save_and_load(self, mem_conn):
        """저장 후 조회 정합성."""
        from src.metrics.store import load_metric, save_metric
        save_metric(mem_conn, "2026-03-23", "TEST_METRIC", 42.5)
        val = load_metric(mem_conn, "2026-03-23", "TEST_METRIC")
        assert val == pytest.approx(42.5)

    def test_upsert_updates_value(self, mem_conn):
        """같은 키로 두 번 저장하면 최신 값으로 덮어쓴다."""
        from src.metrics.store import load_metric, save_metric
        save_metric(mem_conn, "2026-03-23", "TEST_METRIC", 1.0)
        save_metric(mem_conn, "2026-03-23", "TEST_METRIC", 2.0)
        val = load_metric(mem_conn, "2026-03-23", "TEST_METRIC")
        assert val == pytest.approx(2.0)

    def test_load_json(self, mem_conn):
        """JSON 데이터 저장 및 조회."""
        from src.metrics.store import load_metric_json, save_metric
        save_metric(mem_conn, "2026-03-23", "TIDS", 10.0, extra_json={"z12": 80.0})
        result = load_metric_json(mem_conn, "2026-03-23", "TIDS")
        assert result is not None
        assert result["z12"] == pytest.approx(80.0)

    def test_load_series(self, mem_conn):
        """시계열 조회."""
        from src.metrics.store import load_metric_series, save_metric
        save_metric(mem_conn, "2026-03-21", "LSI", 1.1)
        save_metric(mem_conn, "2026-03-22", "LSI", 1.2)
        save_metric(mem_conn, "2026-03-23", "LSI", 1.3)
        series = load_metric_series(mem_conn, "LSI", "2026-03-21", "2026-03-23")
        assert len(series) == 3
        assert series[0][1] == pytest.approx(1.1)
        assert series[-1][1] == pytest.approx(1.3)
