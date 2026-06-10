"""실 데이터(pansongit@gmail.com) 기반 통합 테스트.

session-scoped read-only 연결로 원본 DB 안전.
실 DB 없는 환경(CI)에서 전체 파일 skip.
"""

import json
import re
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from src.db_setup import get_db_path

_REAL_USER = "pansongit@gmail.com"
_REAL_DB = get_db_path(_REAL_USER)

# ── 물리 범위 상수 ──────────────────────────────────────────────────────────
_PACE_MIN, _PACE_MAX = 60, 900
_HR_MIN, _HR_MAX = 40, 250
_DIST_KM_MAX = 300
_CTL_MAX = 300
_TSB_MIN, _TSB_MAX = -300, 150
_ACWR_MAX = 5.0
_VO2MAX_MIN, _VO2MAX_MAX = 20, 90
_TRAINING_LOAD_MAX = 2000
_SLEEP_DUR_MAX = 54000
_HRV_MIN, _HRV_MAX = 1, 200
_RHR_MIN, _RHR_MAX = 25, 100
_SPEED_MAX_MS = 20.0
_CADENCE_MAX = 250
_ALT_MIN, _ALT_MAX = -100, 10000

_VALID_SOURCES = {"strava", "intervals", "garmin"}
_VALID_GRADES = {"A", "B", "C", "D", "F"}
_VALID_ACWR_STATUS = {"low", "safe", "caution", "danger", "unknown"}
_VALID_PHASES = {"tapering", "recovering", "building", "detraining", "maintaining", "unknown"}
_VALID_RECOVERY_GRADES = {"excellent", "good", "moderate", "poor"}
_VALID_POLARIZATION = {"threshold_heavy", "optimal", "too_hard", "too_easy", "unknown"}
_VALID_RECOVERY_TRENDS = {"improving", "declining", "stable", "unknown"}

_TODAY = datetime.today().strftime("%Y-%m-%d")
_4W_AGO = (datetime.today() - timedelta(weeks=4)).strftime("%Y-%m-%d")


@pytest.fixture(scope="session")
def real_conn():
    if not _REAL_DB.exists():
        pytest.skip(f"실 DB 없음: {_REAL_DB}")
    conn = sqlite3.connect(f"file:{_REAL_DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


# ═══════════════════════════════════════════════════════════════════
# Part 1: 원시 데이터 무결성
# ═══════════════════════════════════════════════════════════════════

class TestRawActivitySummaries:
    def test_distance_m_range(self, real_conn):
        rows = real_conn.execute(
            "SELECT distance_m FROM activity_summaries WHERE distance_m IS NOT NULL"
        ).fetchall()
        for r in rows:
            assert 0 <= r["distance_m"] <= 200_000, f"distance_m={r['distance_m']}"

    def test_elapsed_time_range(self, real_conn):
        rows = real_conn.execute(
            "SELECT elapsed_time_sec FROM activity_summaries WHERE elapsed_time_sec IS NOT NULL"
        ).fetchall()
        for r in rows:
            assert 0 <= r["elapsed_time_sec"] <= 86400, f"elapsed={r['elapsed_time_sec']}"

    def test_avg_pace_running_only(self, real_conn):
        rows = real_conn.execute(
            "SELECT avg_pace_sec_km FROM activity_summaries "
            "WHERE activity_type IN ('running','run','virtualrun','treadmill') "
            "AND avg_pace_sec_km IS NOT NULL AND avg_pace_sec_km > 0"
        ).fetchall()
        assert len(rows) > 0, "running 활동에 pace 데이터 없음"
        for r in rows:
            assert _PACE_MIN <= r["avg_pace_sec_km"] <= _PACE_MAX, f"pace={r['avg_pace_sec_km']}"

    def test_hr_range(self, real_conn):
        rows = real_conn.execute(
            "SELECT avg_hr, max_hr FROM activity_summaries "
            "WHERE avg_hr IS NOT NULL OR max_hr IS NOT NULL"
        ).fetchall()
        for r in rows:
            if r["avg_hr"] is not None:
                assert _HR_MIN <= r["avg_hr"] <= _HR_MAX, f"avg_hr={r['avg_hr']}"
            if r["max_hr"] is not None:
                assert _HR_MIN <= r["max_hr"] <= _HR_MAX, f"max_hr={r['max_hr']}"

    def test_elevation_nonneg(self, real_conn):
        rows = real_conn.execute(
            "SELECT elevation_gain FROM activity_summaries WHERE elevation_gain IS NOT NULL"
        ).fetchall()
        for r in rows:
            assert r["elevation_gain"] >= 0, f"elevation={r['elevation_gain']}"

    def test_source_valid(self, real_conn):
        rows = real_conn.execute("SELECT DISTINCT source FROM activity_summaries").fetchall()
        for r in rows:
            assert r["source"] in _VALID_SOURCES, f"unknown source: {r['source']}"

    def test_timestamp_iso(self, real_conn):
        rows = real_conn.execute(
            "SELECT start_time FROM activity_summaries WHERE start_time IS NOT NULL LIMIT 50"
        ).fetchall()
        for r in rows:
            assert re.match(r"\d{4}-\d{2}-\d{2}", r["start_time"]), f"bad timestamp: {r['start_time']}"

    def test_no_duplicate_source_ids(self, real_conn):
        row = real_conn.execute(
            "SELECT COUNT(*) AS total, COUNT(DISTINCT source || '::' || source_id) AS uniq "
            "FROM activity_summaries WHERE source_id IS NOT NULL"
        ).fetchone()
        assert row["total"] == row["uniq"], "source+source_id 중복 존재"


class TestRawWellness:
    def test_sleep_score_range(self, real_conn):
        rows = real_conn.execute(
            "SELECT sleep_score FROM daily_wellness WHERE sleep_score IS NOT NULL"
        ).fetchall()
        for r in rows:
            assert 0 <= r["sleep_score"] <= 100, f"sleep_score={r['sleep_score']}"

    def test_sleep_duration_range(self, real_conn):
        rows = real_conn.execute(
            "SELECT sleep_duration_sec FROM daily_wellness WHERE sleep_duration_sec IS NOT NULL"
        ).fetchall()
        for r in rows:
            assert 0 <= r["sleep_duration_sec"] <= _SLEEP_DUR_MAX, f"sleep_dur={r['sleep_duration_sec']}"

    def test_hrv_range(self, real_conn):
        rows = real_conn.execute(
            "SELECT hrv_last_night FROM daily_wellness WHERE hrv_last_night IS NOT NULL"
        ).fetchall()
        for r in rows:
            assert _HRV_MIN <= r["hrv_last_night"] <= _HRV_MAX, f"hrv={r['hrv_last_night']}"

    def test_resting_hr_range(self, real_conn):
        rows = real_conn.execute(
            "SELECT resting_hr FROM daily_wellness WHERE resting_hr IS NOT NULL"
        ).fetchall()
        for r in rows:
            assert _RHR_MIN <= r["resting_hr"] <= _RHR_MAX, f"rhr={r['resting_hr']}"

    def test_body_battery_range(self, real_conn):
        rows = real_conn.execute(
            "SELECT body_battery_high, body_battery_low FROM daily_wellness "
            "WHERE body_battery_high IS NOT NULL OR body_battery_low IS NOT NULL"
        ).fetchall()
        for r in rows:
            if r["body_battery_high"] is not None:
                assert 0 <= r["body_battery_high"] <= 100, f"bb_high={r['body_battery_high']}"
            if r["body_battery_low"] is not None:
                assert 0 <= r["body_battery_low"] <= 100, f"bb_low={r['body_battery_low']}"

    def test_stress_range(self, real_conn):
        rows = real_conn.execute(
            "SELECT avg_stress FROM daily_wellness WHERE avg_stress IS NOT NULL"
        ).fetchall()
        for r in rows:
            assert 0 <= r["avg_stress"] <= 100, f"stress={r['avg_stress']}"

    def test_weight_range(self, real_conn):
        rows = real_conn.execute(
            "SELECT weight_kg FROM daily_wellness WHERE weight_kg IS NOT NULL"
        ).fetchall()
        for r in rows:
            assert 30 <= r["weight_kg"] <= 200, f"weight={r['weight_kg']}"

    def test_no_duplicate_dates(self, real_conn):
        row = real_conn.execute(
            "SELECT COUNT(*) AS total, COUNT(DISTINCT date) AS uniq FROM daily_wellness"
        ).fetchone()
        assert row["total"] == row["uniq"], "daily_wellness date 중복"


class TestRawMetricStore:
    def test_ctl_atl_range(self, real_conn):
        rows = real_conn.execute(
            "SELECT numeric_value FROM metric_store "
            "WHERE metric_name IN ('ctl','atl') AND numeric_value IS NOT NULL"
        ).fetchall()
        for r in rows:
            assert 0 <= r["numeric_value"] <= _CTL_MAX, f"ctl/atl={r['numeric_value']}"

    def test_tsb_range(self, real_conn):
        rows = real_conn.execute(
            "SELECT numeric_value FROM metric_store WHERE metric_name='tsb' AND numeric_value IS NOT NULL"
        ).fetchall()
        for r in rows:
            assert _TSB_MIN <= r["numeric_value"] <= _TSB_MAX, f"tsb={r['numeric_value']}"

    def test_acwr_range(self, real_conn):
        rows = real_conn.execute(
            "SELECT numeric_value FROM metric_store WHERE metric_name='acwr' AND numeric_value IS NOT NULL"
        ).fetchall()
        for r in rows:
            assert 0 <= r["numeric_value"] <= _ACWR_MAX, f"acwr={r['numeric_value']}"

    def test_vo2max_range(self, real_conn):
        rows = real_conn.execute(
            "SELECT numeric_value FROM metric_store "
            "WHERE metric_name LIKE '%vo2max%' AND numeric_value IS NOT NULL"
        ).fetchall()
        for r in rows:
            assert _VO2MAX_MIN <= r["numeric_value"] <= _VO2MAX_MAX, f"vo2max={r['numeric_value']}"

    def test_training_load_range(self, real_conn):
        rows = real_conn.execute(
            "SELECT numeric_value FROM metric_store "
            "WHERE metric_name='training_load' AND numeric_value IS NOT NULL"
        ).fetchall()
        for r in rows:
            assert 0 <= r["numeric_value"] <= _TRAINING_LOAD_MAX, f"training_load={r['numeric_value']}"

    def test_hr_zone_sec_range(self, real_conn):
        rows = real_conn.execute(
            "SELECT numeric_value FROM metric_store "
            "WHERE metric_name LIKE 'hr_zone_%_sec' AND numeric_value IS NOT NULL"
        ).fetchall()
        for r in rows:
            assert 0 <= r["numeric_value"] <= 86400, f"hr_zone_sec={r['numeric_value']}"

    def test_is_primary_uniqueness(self, real_conn):
        row = real_conn.execute("""
            SELECT COUNT(*) AS dups FROM (
                SELECT metric_name, scope_type, scope_id, provider, COUNT(*) AS cnt
                FROM metric_store
                WHERE is_primary=1
                GROUP BY metric_name, scope_type, scope_id, provider
                HAVING cnt > 1
            )
        """).fetchone()
        assert row["dups"] == 0, f"is_primary=1 중복 {row['dups']}건"


class TestRawActivityStreams:
    def test_heart_rate_range(self, real_conn):
        row = real_conn.execute(
            "SELECT MIN(heart_rate) AS mn, MAX(heart_rate) AS mx "
            "FROM activity_streams WHERE heart_rate IS NOT NULL"
        ).fetchone()
        if row["mn"] is not None:
            assert _HR_MIN <= row["mn"], f"min heart_rate={row['mn']}"
            assert row["mx"] <= _HR_MAX, f"max heart_rate={row['mx']}"

    def test_cadence_range(self, real_conn):
        row = real_conn.execute(
            "SELECT MIN(cadence) AS mn, MAX(cadence) AS mx "
            "FROM activity_streams WHERE cadence IS NOT NULL"
        ).fetchone()
        if row["mn"] is not None:
            assert 0 <= row["mn"]
            assert row["mx"] <= _CADENCE_MAX, f"max cadence={row['mx']}"

    def test_speed_ms_range(self, real_conn):
        row = real_conn.execute(
            "SELECT MIN(speed_ms) AS mn, MAX(speed_ms) AS mx "
            "FROM activity_streams WHERE speed_ms IS NOT NULL"
        ).fetchone()
        if row["mn"] is not None:
            assert 0 <= row["mn"]
            assert row["mx"] <= _SPEED_MAX_MS, f"max speed_ms={row['mx']}"

    def test_altitude_range(self, real_conn):
        row = real_conn.execute(
            "SELECT MIN(altitude_m) AS mn, MAX(altitude_m) AS mx "
            "FROM activity_streams WHERE altitude_m IS NOT NULL"
        ).fetchone()
        if row["mn"] is not None:
            assert _ALT_MIN <= row["mn"], f"min altitude={row['mn']}"
            assert row["mx"] <= _ALT_MAX, f"max altitude={row['mx']}"

    def test_lat_lon_bounds(self, real_conn):
        row = real_conn.execute(
            "SELECT MIN(latitude) AS min_lat, MAX(latitude) AS max_lat, "
            "MIN(longitude) AS min_lon, MAX(longitude) AS max_lon "
            "FROM activity_streams WHERE latitude IS NOT NULL AND longitude IS NOT NULL"
        ).fetchone()
        if row["min_lat"] is not None:
            assert -90 <= row["min_lat"] <= 90, f"min_lat={row['min_lat']}"
            assert -90 <= row["max_lat"] <= 90, f"max_lat={row['max_lat']}"
            assert -180 <= row["min_lon"] <= 180, f"min_lon={row['min_lon']}"
            assert -180 <= row["max_lon"] <= 180, f"max_lon={row['max_lon']}"


class TestRawCanonicalView:
    def test_no_source_id_dupes(self, real_conn):
        row = real_conn.execute(
            "SELECT COUNT(*) AS total, COUNT(DISTINCT source || '::' || source_id) AS uniq "
            "FROM v_canonical_activities WHERE source_id IS NOT NULL"
        ).fetchone()
        assert row["total"] == row["uniq"], "canonical 내 source_id 중복"

    def test_canonical_lte_summaries(self, real_conn):
        canonical = real_conn.execute("SELECT COUNT(*) AS n FROM v_canonical_activities").fetchone()["n"]
        total = real_conn.execute("SELECT COUNT(*) AS n FROM activity_summaries").fetchone()["n"]
        assert canonical <= total, f"canonical({canonical}) > summaries({total})"

    def test_valid_sources(self, real_conn):
        rows = real_conn.execute("SELECT DISTINCT source FROM v_canonical_activities").fetchall()
        for r in rows:
            assert r["source"] in _VALID_SOURCES, f"unknown source: {r['source']}"

    def test_distance_range(self, real_conn):
        rows = real_conn.execute(
            "SELECT distance_m FROM v_canonical_activities WHERE distance_m IS NOT NULL"
        ).fetchall()
        for r in rows:
            assert 0 <= r["distance_m"] <= 200_000, f"distance_m={r['distance_m']}"


# ═══════════════════════════════════════════════════════════════════
# Part 2: 분석 파이프라인
# ═══════════════════════════════════════════════════════════════════

class TestTrendsRangesReal:
    def test_weekly_distances_in_km(self, real_conn):
        from src.analysis.trends import weekly_trends
        results = weekly_trends(real_conn, weeks=52)
        assert isinstance(results, list)
        for w in results:
            dist = w.get("total_distance_km")
            if dist is not None:
                assert 0 <= dist <= _DIST_KM_MAX, f"weekly_dist={dist}"

    def test_weekly_pace_running(self, real_conn):
        from src.analysis.trends import weekly_trends
        results = weekly_trends(real_conn, weeks=52)
        for w in results:
            pace = w.get("avg_pace_sec_km")
            if pace is not None:
                assert _PACE_MIN <= pace <= _PACE_MAX, f"weekly_pace={pace}"

    def test_fitness_ctl_atl_range(self, real_conn):
        from src.analysis.trends import fitness_trend
        results = fitness_trend(real_conn, weeks=52)
        assert isinstance(results, list)
        for r in results:
            if r.get("ctl") is not None:
                assert 0 <= r["ctl"] <= _CTL_MAX, f"ctl={r['ctl']}"
            if r.get("atl") is not None:
                assert 0 <= r["atl"] <= _CTL_MAX, f"atl={r['atl']}"

    def test_fitness_tsb_range(self, real_conn):
        from src.analysis.trends import fitness_trend
        results = fitness_trend(real_conn, weeks=52)
        for r in results:
            if r.get("tsb") is not None:
                assert _TSB_MIN <= r["tsb"] <= _TSB_MAX, f"tsb={r['tsb']}"

    def test_nonzero_weeks_count(self, real_conn):
        from src.analysis.trends import weekly_trends
        results = weekly_trends(real_conn, weeks=52)
        nonzero = [w for w in results if (w.get("total_distance_km") or 0) > 0]
        assert len(nonzero) >= 1, "거리 > 0 인 주가 없음"


class TestCompareRangesReal:
    def _check_keys(self, result):
        for key in ("period1", "period2", "delta", "pct"):
            assert key in result, f"'{key}' 키 없음"

    def test_compare_periods_keys(self, real_conn):
        from src.analysis.compare import compare_periods
        p1_start = (datetime.today() - timedelta(weeks=8)).strftime("%Y-%m-%d")
        result = compare_periods(real_conn, p1_start, _4W_AGO, _4W_AGO, _TODAY)
        self._check_keys(result)

    def test_compare_periods_delta_math(self, real_conn):
        from src.analysis.compare import compare_periods
        p1_start = (datetime.today() - timedelta(weeks=8)).strftime("%Y-%m-%d")
        result = compare_periods(real_conn, p1_start, _4W_AGO, _4W_AGO, _TODAY)
        d1 = result["period1"].get("total_distance_km") or 0
        d2 = result["period2"].get("total_distance_km") or 0
        delta = result["delta"].get("total_distance_km") or 0
        assert abs(delta - (d2 - d1)) < 0.01, f"delta mismatch: {delta} != {d2}-{d1}"

    def test_compare_this_week_vs_last(self, real_conn):
        from src.analysis.compare import compare_this_week_vs_last
        result = compare_this_week_vs_last(real_conn)
        self._check_keys(result)
        for pk in ("period1", "period2"):
            dist = result[pk].get("total_distance_km") or 0
            assert 0 <= dist < 500, f"{pk}.dist={dist}"

    def test_compare_today_vs_yesterday(self, real_conn):
        from src.analysis.compare import compare_today_vs_yesterday
        result = compare_today_vs_yesterday(real_conn)
        self._check_keys(result)

    def test_compare_this_month_vs_last(self, real_conn):
        from src.analysis.compare import compare_this_month_vs_last
        result = compare_this_month_vs_last(real_conn)
        self._check_keys(result)
        for pk in ("period1", "period2"):
            dist = result[pk].get("total_distance_km") or 0
            assert 0 <= dist < 500, f"{pk}.dist={dist}"


class TestWeeklyScoreRangesReal:
    def _monday(self, weeks_ago: int = 0) -> str:
        today = datetime.today()
        monday = today - timedelta(days=today.weekday()) - timedelta(weeks=weeks_ago)
        return monday.strftime("%Y-%m-%d")

    def test_score_range(self, real_conn):
        from src.analysis.weekly_score import calculate_weekly_score
        for week_offset in range(4):
            result = calculate_weekly_score(real_conn, week_start=self._monday(week_offset))
            score = result.get("total_score")
            if score is not None:
                assert 0 <= score <= 100, f"score={score} (week -{week_offset})"

    def test_grade_valid(self, real_conn):
        from src.analysis.weekly_score import calculate_weekly_score
        for week_offset in range(4):
            result = calculate_weekly_score(real_conn, week_start=self._monday(week_offset))
            grade = result.get("grade")
            if grade is not None:
                assert grade in _VALID_GRADES, f"grade={grade}"

    def test_components_non_negative(self, real_conn):
        from src.analysis.weekly_score import calculate_weekly_score
        result = calculate_weekly_score(real_conn, week_start=self._monday())
        components = result.get("components") or {}
        for k, v in components.items():
            if v is not None:
                assert v >= 0, f"component {k}={v}"


class TestRaceReadinessRangesReal:
    def test_readiness_score_range(self, real_conn):
        from src.analysis.race_readiness import assess_race_readiness
        result = assess_race_readiness(real_conn)
        score = result.get("readiness_score")
        if score is not None:
            assert 0 <= score <= 100, f"readiness_score={score}"

    def test_grade_valid(self, real_conn):
        from src.analysis.race_readiness import assess_race_readiness
        result = assess_race_readiness(real_conn)
        grade = result.get("grade")
        if grade is not None:
            assert grade in _VALID_GRADES, f"grade={grade}"

    def test_predictions_range(self, real_conn):
        from src.analysis.race_readiness import assess_race_readiness
        result = assess_race_readiness(real_conn)
        preds = result.get("predictions") or {}
        if preds.get("5k") is not None:
            assert 600 <= preds["5k"] <= 3600, f"5k={preds['5k']}"
        if preds.get("10k") is not None:
            assert 1200 <= preds["10k"] <= 7200, f"10k={preds['10k']}"
        if preds.get("half") is not None:
            assert 3000 <= preds["half"] <= 14400, f"half={preds['half']}"
        if preds.get("full") is not None:
            assert 7200 <= preds["full"] <= 28800, f"full={preds['full']}"

    def test_component_scores_range(self, real_conn):
        from src.analysis.race_readiness import assess_race_readiness
        result = assess_race_readiness(real_conn)
        scores = result.get("scores") or {}
        for k, v in scores.items():
            if v is not None:
                assert 0 <= v <= 100, f"score[{k}]={v}"

    def test_vdot_race_predictions(self, real_conn):
        from src.analysis.race_readiness import vdot_race_predictions
        preds = vdot_race_predictions(50.0)
        assert preds is not None
        assert 600 <= preds["5k"] <= 3600
        assert 1200 <= preds["10k"] <= 7200
        assert 3000 <= preds["half"] <= 14400
        assert 7200 <= preds["full"] <= 28800


class TestActivityDeepRangesReal:
    @pytest.fixture(scope="class")
    def recent_run_ids(self, real_conn):
        rows = real_conn.execute(
            "SELECT id FROM activity_summaries "
            "WHERE activity_type IN ('running','run','virtualrun','treadmill') "
            "ORDER BY start_time DESC LIMIT 5"
        ).fetchall()
        ids = [r["id"] for r in rows]
        if not ids:
            pytest.skip("러닝 활동 없음")
        return ids

    def test_structure_keys(self, real_conn, recent_run_ids):
        from src.analysis.activity_deep import deep_analyze
        result = deep_analyze(real_conn, recent_run_ids[0])
        # activity_deep returns 'core' or 'activity' depending on version
        assert "activity" in result or "core" in result, f"구조키 없음: {list(result.keys())}"

    def test_pace_format_or_none(self, real_conn, recent_run_ids):
        from src.analysis.activity_deep import deep_analyze
        for aid in recent_run_ids:
            result = deep_analyze(real_conn, aid)
            act = result.get("activity") or result.get("core") or {}
            pace = act.get("avg_pace")
            if pace is not None:
                assert re.match(r"^\d+:\d{2}$", str(pace)), f"pace format={pace}"

    def test_distance_km_unit(self, real_conn, recent_run_ids):
        from src.analysis.activity_deep import deep_analyze
        for aid in recent_run_ids:
            result = deep_analyze(real_conn, aid)
            act = result.get("activity") or result.get("core") or {}
            dist_km = act.get("distance_km")
            if dist_km is not None:
                assert 0 < dist_km < _DIST_KM_MAX, f"distance_km={dist_km} — m 단위 혼입 의심"

    def test_hr_in_range(self, real_conn, recent_run_ids):
        from src.analysis.activity_deep import deep_analyze
        for aid in recent_run_ids:
            result = deep_analyze(real_conn, aid)
            act = result.get("activity") or result.get("core") or {}
            if act.get("avg_hr") is not None:
                assert _HR_MIN <= act["avg_hr"] <= _HR_MAX, f"avg_hr={act['avg_hr']}"
            if act.get("max_hr") is not None:
                assert _HR_MIN <= act["max_hr"] <= _HR_MAX, f"max_hr={act['max_hr']}"


class TestEfficiencyRangesReal:
    @pytest.fixture(scope="class")
    def run_with_streams_id(self, real_conn):
        row = real_conn.execute(
            "SELECT DISTINCT a.id FROM activity_summaries a "
            "JOIN activity_streams s ON a.id = s.activity_id "
            "WHERE a.activity_type IN ('running','run','virtualrun','treadmill') "
            "ORDER BY a.start_time DESC LIMIT 1"
        ).fetchone()
        if row is None:
            pytest.skip("스트림 있는 러닝 활동 없음")
        return row["id"]

    def test_calculate_efficiency_structure(self, real_conn, run_with_streams_id):
        from src.analysis.efficiency import calculate_efficiency
        result = calculate_efficiency(real_conn, run_with_streams_id)
        if result is None:
            pytest.skip("efficiency 계산 데이터 부족")
        assert "status" in result
        assert result["status"] in {"good", "fair", "poor"}

    def test_decoupling_pct_range(self, real_conn, run_with_streams_id):
        from src.analysis.efficiency import calculate_efficiency
        result = calculate_efficiency(real_conn, run_with_streams_id)
        if result is None:
            pytest.skip("efficiency 계산 데이터 부족")
        dec = result.get("decoupling_pct")
        if dec is not None:
            assert -50 <= dec <= 100, f"decoupling={dec}"

    def test_efficiency_trend_structure(self, real_conn):
        from src.analysis.efficiency import efficiency_trend
        results = efficiency_trend(real_conn, weeks=8)
        assert isinstance(results, list)

    def test_efficiency_trend_ef_values(self, real_conn):
        from src.analysis.efficiency import efficiency_trend
        results = efficiency_trend(real_conn, weeks=8)
        for w in results:
            ef = w.get("avg_ef")
            if ef is not None:
                assert 0 < ef < 5, f"avg_ef={ef}"


class TestRecoveryRangesReal:
    def test_recovery_status_always_dict(self, real_conn):
        from src.analysis.recovery import get_recovery_status
        result = get_recovery_status(real_conn)
        assert isinstance(result, dict)
        assert "available" in result

    def test_recovery_score_range(self, real_conn):
        from src.analysis.recovery import get_recovery_status
        result = get_recovery_status(real_conn)
        score = result.get("recovery_score")
        if score is not None:
            assert 0 <= score <= 100, f"recovery_score={score}"

    def test_recovery_grade_valid(self, real_conn):
        from src.analysis.recovery import get_recovery_status
        result = get_recovery_status(real_conn)
        grade = result.get("grade")
        if grade is not None:
            assert grade in _VALID_RECOVERY_GRADES, f"grade={grade}"

    def test_recovery_trend_structure(self, real_conn):
        from src.analysis.recovery import recovery_trend
        result = recovery_trend(real_conn, days=14)
        assert "scores" in result
        assert "trend" in result
        assert result["trend"] in _VALID_RECOVERY_TRENDS
        assert isinstance(result["scores"], list)


class TestZonesRangesReal:
    def test_analyze_zones_structure(self, real_conn):
        from src.analysis.zones_analysis import analyze_zones
        result = analyze_zones(real_conn, _4W_AGO, _TODAY)
        assert "zone_distribution" in result
        assert "polarization_status" in result
        assert result["polarization_status"] in _VALID_POLARIZATION

    def test_zone_pct_sums(self, real_conn):
        from src.analysis.zones_analysis import analyze_zones
        result = analyze_zones(real_conn, _4W_AGO, _TODAY)
        dist = result.get("zone_distribution") or {}
        total_pct = sum(z.get("pct", 0) for z in dist.values())
        if total_pct > 0:
            assert abs(total_pct - 100) < 2, f"zone pct 합={total_pct}"

    def test_weekly_zone_trend_length(self, real_conn):
        from src.analysis.zones_analysis import weekly_zone_trend
        results = weekly_zone_trend(real_conn, weeks=4)
        assert len(results) == 4

    def test_weekly_zone_trend_pct_range(self, real_conn):
        from src.analysis.zones_analysis import weekly_zone_trend
        results = weekly_zone_trend(real_conn, weeks=4)
        for w in results:
            for key in ("easy_pct", "hard_pct", "moderate_pct"):
                val = w.get(key) or 0
                assert 0 <= val <= 100, f"{key}={val}"


# ═══════════════════════════════════════════════════════════════════
# Part 3: 서비스 레이어
# ═══════════════════════════════════════════════════════════════════

class TestSuggestionsRangesReal:
    def test_acwr_status_valid(self, real_conn):
        from src.ai.suggestions import get_runner_state
        state = get_runner_state(real_conn)
        assert state.acwr_status in _VALID_ACWR_STATUS

    def test_weekly_run_count_plausible(self, real_conn):
        from src.ai.suggestions import get_runner_state
        state = get_runner_state(real_conn)
        assert 0 <= state.weekly_run_count <= 7

    def test_chips_count_range(self, real_conn):
        from src.ai.suggestions import get_runner_state, rule_based_chips
        state = get_runner_state(real_conn)
        chips = rule_based_chips(state)
        assert 1 <= len(chips) <= 5, f"chips={len(chips)}"

    def test_chips_keys(self, real_conn):
        from src.ai.suggestions import get_runner_state, rule_based_chips
        state = get_runner_state(real_conn)
        chips = rule_based_chips(state)
        for chip in chips:
            assert "id" in chip, f"chip에 'id' 없음: {chip}"
            assert "label" in chip, f"chip에 'label' 없음: {chip}"

    def test_no_exception(self, real_conn):
        from src.ai.suggestions import get_runner_state, rule_based_chips
        state = get_runner_state(real_conn)
        chips = rule_based_chips(state)
        assert state is not None and chips is not None


class TestDashboardRangesReal:
    @pytest.fixture(scope="class")
    def dashboard(self, real_conn):
        from src.services.dashboard_service import get_dashboard_data
        return get_dashboard_data(real_conn)

    def test_required_keys(self, dashboard):
        for key in ("wellness", "training_status", "recent_activities", "weekly_summary"):
            assert key in dashboard, f"'{key}' 키 없음"

    def test_training_phase_valid(self, dashboard):
        phase = (dashboard.get("training_status") or {}).get("phase")
        if phase is not None:
            assert phase in _VALID_PHASES, f"phase={phase}"

    def test_weekly_summary_non_negative(self, dashboard):
        ws = dashboard.get("weekly_summary") or {}
        for k, v in ws.items():
            if v is not None and isinstance(v, (int, float)):
                assert v >= 0, f"weekly_summary.{k}={v}"

    def test_ctl_when_present(self, dashboard):
        ctl = (dashboard.get("training_status") or {}).get("ctl")
        if ctl is not None:
            assert 0 <= ctl <= _CTL_MAX, f"ctl={ctl}"

    def test_pmc_chart_sorted(self, real_conn):
        from src.services.dashboard_service import get_pmc_chart_data
        results = get_pmc_chart_data(real_conn, days=90)
        assert isinstance(results, list)
        if len(results) >= 2:
            dates = [r["date"] for r in results]
            assert dates == sorted(dates), "pmc_chart 날짜 비정렬"

    def test_pmc_chart_values(self, real_conn):
        from src.services.dashboard_service import get_pmc_chart_data
        results = get_pmc_chart_data(real_conn, days=90)
        for r in results:
            if r.get("ctl") is not None:
                assert 0 <= r["ctl"] <= _CTL_MAX, f"ctl={r['ctl']}"
            if r.get("tsb") is not None:
                assert _TSB_MIN <= r["tsb"] <= _TSB_MAX, f"tsb={r['tsb']}"

    def test_daily_metric_chart(self, real_conn):
        from src.services.dashboard_service import get_daily_metric_chart
        results = get_daily_metric_chart(real_conn, "ctl", days=30)
        assert isinstance(results, list)
        for r in results:
            assert "date" in r
            assert "value" in r
            assert 0 <= r["value"] <= _CTL_MAX, f"ctl value={r['value']}"


class TestWellnessRangesReal:
    def test_detail_is_dict(self, real_conn):
        from src.services.wellness_service import get_wellness_detail
        result = get_wellness_detail(real_conn)
        assert isinstance(result, dict)

    def test_hrv_range(self, real_conn):
        from src.services.wellness_service import get_wellness_detail
        result = get_wellness_detail(real_conn)
        core = result.get("core") or result
        hrv = core.get("hrv_last_night")
        if hrv is not None:
            assert _HRV_MIN <= hrv <= _HRV_MAX, f"hrv={hrv}"

    def test_resting_hr_range(self, real_conn):
        from src.services.wellness_service import get_wellness_detail
        result = get_wellness_detail(real_conn)
        core = result.get("core") or result
        rhr = core.get("resting_hr")
        if rhr is not None:
            assert _RHR_MIN <= rhr <= _RHR_MAX, f"rhr={rhr}"

    def test_sleep_score_range(self, real_conn):
        from src.services.wellness_service import get_wellness_detail
        result = get_wellness_detail(real_conn)
        core = result.get("core") or result
        score = core.get("sleep_score")
        if score is not None:
            assert 0 <= score <= 100, f"sleep_score={score}"

    def test_trend_arrays_same_length(self, real_conn):
        from src.services.wellness_service import get_wellness_trend
        result = get_wellness_trend(real_conn)
        assert isinstance(result, dict)
        arrays = {k: result[k] for k in ("dates", "sleep_score", "hrv_last_night", "resting_hr") if k in result and result[k] is not None}
        lengths = {k: len(v) for k, v in arrays.items()}
        assert len(set(lengths.values())) <= 1, f"배열 길이 불일치: {lengths}"


class TestActivityServiceRangesReal:
    def test_list_pagination(self, real_conn):
        from src.services.activity_service import get_activity_list
        result = get_activity_list(real_conn, per_page=10)
        items = result.get("activities", [])
        assert len(items) <= 10

    def test_list_distance_km(self, real_conn):
        from src.services.activity_service import get_activity_list
        result = get_activity_list(real_conn, per_page=20)
        items = result.get("activities", [])
        for item in items:
            dist = item.get("distance_km")
            if dist is not None:
                assert 0 <= dist <= _DIST_KM_MAX, f"distance_km={dist}"

    def test_detail_structure(self, real_conn):
        from src.services.activity_service import get_activity_list, get_activity_detail
        result = get_activity_list(real_conn, filters={"activity_type": "running"}, per_page=3)
        items = result.get("activities", [])
        if not items:
            pytest.skip("러닝 활동 없음")
        detail = get_activity_detail(real_conn, items[0]["id"])
        # get_activity_detail returns {'core': {...}, 'metrics_by_category': {...}, ...}
        assert "core" in detail, f"'core' 키 없음: {list(detail.keys())}"

    def test_filter_sport(self, real_conn):
        from src.services.activity_service import get_activity_list
        result = get_activity_list(real_conn, filters={"activity_type": "running"}, per_page=10)
        items = result.get("activities", [])
        for item in items:
            sport = item.get("sport") or item.get("activity_type", "")
            assert "run" in sport.lower(), f"sport 필터 오류: {sport}"

    def test_streams_values(self, real_conn):
        from src.services.activity_service import get_activity_list, get_activity_streams
        result = get_activity_list(real_conn, filters={"activity_type": "running"}, per_page=5)
        items = result.get("activities", [])
        for item in items:
            streams = get_activity_streams(real_conn, item["id"])
            if streams:
                for pt in streams[:100]:
                    if pt.get("heart_rate") is not None:
                        assert _HR_MIN <= pt["heart_rate"] <= _HR_MAX
                    if pt.get("speed_ms") is not None:
                        assert 0 <= pt["speed_ms"] <= _SPEED_MAX_MS
                break


class TestUnifiedViewRangesReal:
    @pytest.fixture(scope="class")
    def unified_page(self, real_conn):
        from src.services.unified_view import fetch_unified_activities
        activities, total, meta = fetch_unified_activities(real_conn, page=1, page_size=10)
        return activities, total, meta

    def test_pagination(self, unified_page):
        activities, total, _ = unified_page
        assert isinstance(activities, list)
        assert len(activities) <= 10
        assert total >= len(activities)

    def test_distance_km_range(self, unified_page):
        activities, _, _ = unified_page
        for ua in activities:
            dist_m = ua.distance_m.value
            if dist_m is not None:
                dist_km = dist_m / 1000
                assert 0 <= dist_km <= _DIST_KM_MAX, f"distance_km={dist_km}"

    def test_meta_keys(self, unified_page):
        _, _, meta = unified_page
        assert "total_count" in meta
        assert "total_dist_km" in meta

    def test_source_comparison(self, real_conn):
        from src.services.unified_view import fetch_unified_activities, build_source_comparison
        activities, _, _ = fetch_unified_activities(real_conn, page=1, page_size=5)
        for ua in activities:
            if ua.source_rows:
                comparison = build_source_comparison(ua.source_rows)
                assert isinstance(comparison, list)
                break


# ═══════════════════════════════════════════════════════════════════
# Part 4: 보조 검증
# ═══════════════════════════════════════════════════════════════════

class TestDedupIntegrity:
    def test_group_source_uniqueness(self, real_conn):
        row = real_conn.execute("""
            SELECT COUNT(*) AS violations FROM (
                SELECT matched_group_id, COUNT(DISTINCT source) AS src_count
                FROM activity_summaries
                WHERE matched_group_id IS NOT NULL
                GROUP BY matched_group_id
                HAVING src_count > 2
            )
        """).fetchone()
        assert row["violations"] == 0, f"group 내 source 3종 이상: {row['violations']}건"

    def test_canonical_ratio_plausible(self, real_conn):
        canonical = real_conn.execute("SELECT COUNT(*) AS n FROM v_canonical_activities").fetchone()["n"]
        total = real_conn.execute("SELECT COUNT(*) AS n FROM activity_summaries").fetchone()["n"]
        ratio = canonical / total if total > 0 else 1.0
        assert 0.3 <= ratio <= 1.0, f"canonical/total={ratio:.2f}"

    def test_no_orphan_canonical(self, real_conn):
        row = real_conn.execute("""
            SELECT COUNT(*) AS orphans FROM v_canonical_activities v
            WHERE NOT EXISTS (
                SELECT 1 FROM activity_summaries a WHERE a.id = v.id
            )
        """).fetchone()
        assert row["orphans"] == 0, f"canonical 내 고아 활동: {row['orphans']}건"


class TestExportRangesReal:
    def test_distance_km_from_canonical(self, real_conn):
        rows = real_conn.execute(
            "SELECT distance_m / 1000.0 AS distance_km "
            "FROM v_canonical_activities WHERE distance_m IS NOT NULL"
        ).fetchall()
        for r in rows:
            assert 0 <= r["distance_km"] <= _DIST_KM_MAX, f"distance_km={r['distance_km']}"

    def test_pace_conversion_plausible(self, real_conn):
        rows = real_conn.execute(
            "SELECT avg_pace_sec_km FROM v_canonical_activities "
            "WHERE activity_type IN ('running','run','virtualrun','treadmill') "
            "AND avg_pace_sec_km IS NOT NULL AND avg_pace_sec_km > 0"
        ).fetchall()
        for r in rows:
            assert _PACE_MIN <= r["avg_pace_sec_km"] <= _PACE_MAX, f"pace={r['avg_pace_sec_km']}"


# ═══════════════════════════════════════════════════════════════════
# Part 5: 전체 메트릭 커버리지 (metric_registry.py SSOT 기반)
# ═══════════════════════════════════════════════════════════════════

_UNIT_BOUNDS: dict[str, tuple] = {
    "sec":       (0, 86400),
    "bpm":       (40, 250),
    "%":         (0, 100),
    "W":         (0, 2000),
    "m/s":       (0, 20),
    "ms":        (0, 10000),
    "ml/kg/min": (20, 90),
    "sec/km":    (60, 900),
    "kg":        (30, 200),
    "kJ":        (0, 100_000),
    "kN/m":      (0, 100),
    "brpm":      (0, 100),
    "score":     (0, 2000),
    "AU":        (0, 50_000),
    "min":       (0, 2880),
    "count":     (0, 1_000_000),
    "kcal":      (0, 20_000),
    "ml":        (0, 10_000),
    "°C":        (-40, 60),
    "hPa":       (800, 1100),
    "ratio":     (0, 10),
    "m":         (0, 200_000),
    "cm":        (0, 500),
}

# activity_summaries: Part 1에서 미검증 수치 컬럼
_ACTIVITY_SUMMARY_EXTRA_COLS: list[tuple] = [
    ("duration_sec",                 0,     86400),
    ("moving_time_sec",              0,     86400),
    ("elevation_loss",               0,     10000),
    ("avg_speed_ms",                 0,     20),
    ("max_speed_ms",                 0,     30),
    ("avg_cadence",                  0,     250),
    ("max_cadence",                  0,     250),
    ("avg_ground_contact_time_ms",   100,   1000),
    ("avg_stride_length_cm",         30,    400),
    ("avg_vertical_oscillation_cm",  1,     30),
    ("avg_vertical_ratio_pct",       0,     30),
    ("avg_power",                    0,     2000),
    ("max_power",                    0,     2000),
    ("avg_temperature",              -40,   60),
    ("start_lat",                    -90,   90),
    ("start_lon",                    -180,  180),
    ("end_lat",                      -90,   90),
    ("end_lon",                      -180,  180),
]

# daily_wellness: Part 1에서 미검증 수치 컬럼
_WELLNESS_EXTRA_COLS: list[tuple] = [
    ("hrv_weekly_avg",  1,    200),
    ("steps",           0,    100_000),
    ("active_calories", 0,    10_000),
]


def _build_metric_store_params() -> list[tuple]:
    from src.utils.metric_registry import list_by_storage
    seen: set[str] = set()
    skip = {
        "ctl", "atl", "tsb", "acwr", "vo2max", "vo2max_activity",
        "effective_vo2max", "training_load",
        "hr_zone_1_sec", "hr_zone_2_sec", "hr_zone_3_sec",
        "hr_zone_4_sec", "hr_zone_5_sec",
    }
    params: list[tuple] = []
    for md in list_by_storage("metric"):
        if md.name in skip or md.name in seen:
            continue
        if md.unit not in _UNIT_BOUNDS:
            continue
        lo, hi = _UNIT_BOUNDS[md.unit]
        params.append((md.name, lo, hi))
        seen.add(md.name)
    return params


_METRIC_STORE_PARAMS = _build_metric_store_params()


class TestAllActivitySummaryColumns:
    """activity_summaries 미검증 수치 컬럼 범위 검증."""

    @pytest.mark.parametrize("col,lo,hi", _ACTIVITY_SUMMARY_EXTRA_COLS)
    def test_column_range(self, real_conn, col, lo, hi):
        row = real_conn.execute(
            f"SELECT MIN({col}) AS mn, MAX({col}) AS mx "
            f"FROM activity_summaries WHERE {col} IS NOT NULL"
        ).fetchone()
        if row["mn"] is None:
            pytest.skip(f"{col} 데이터 없음")
        assert lo <= row["mn"], f"{col} min={row['mn']} < {lo}"
        assert row["mx"] <= hi, f"{col} max={row['mx']} > {hi}"


class TestAllWellnessColumns:
    """daily_wellness 미검증 컬럼 범위 검증."""

    @pytest.mark.parametrize("col,lo,hi", _WELLNESS_EXTRA_COLS)
    def test_column_range(self, real_conn, col, lo, hi):
        row = real_conn.execute(
            f"SELECT MIN({col}) AS mn, MAX({col}) AS mx "
            f"FROM daily_wellness WHERE {col} IS NOT NULL"
        ).fetchone()
        if row["mn"] is None:
            pytest.skip(f"{col} 데이터 없음")
        assert lo <= row["mn"], f"{col} min={row['mn']} < {lo}"
        assert row["mx"] <= hi, f"{col} max={row['mx']} > {hi}"

    def test_sleep_start_time_exists(self, real_conn):
        rows = real_conn.execute(
            "SELECT sleep_start_time FROM daily_wellness "
            "WHERE sleep_start_time IS NOT NULL LIMIT 5"
        ).fetchall()
        if not rows:
            pytest.skip("sleep_start_time 데이터 없음")
        for r in rows:
            assert r["sleep_start_time"] is not None


class TestAllMetricStoreRanges:
    """metric_registry storage='metric' 중 단위 기반 수치 범위 검증."""

    @pytest.mark.parametrize("metric_name,lo,hi", _METRIC_STORE_PARAMS)
    def test_metric_range(self, real_conn, metric_name, lo, hi):
        row = real_conn.execute(
            "SELECT MIN(numeric_value) AS mn, MAX(numeric_value) AS mx "
            "FROM metric_store WHERE metric_name = ? AND numeric_value IS NOT NULL",
            (metric_name,),
        ).fetchone()
        if row["mn"] is None:
            pytest.skip(f"{metric_name} 데이터 없음")
        assert lo <= row["mn"], f"{metric_name} min={row['mn']} < {lo}"
        assert row["mx"] <= hi, f"{metric_name} max={row['mx']} > {hi}"


class TestAllLapsRanges:
    """activity_laps 핵심 컬럼 범위 검증."""

    @pytest.fixture(scope="class")
    def has_laps(self, real_conn):
        try:
            cnt = real_conn.execute(
                "SELECT COUNT(*) AS n FROM activity_laps"
            ).fetchone()["n"]
        except Exception:
            pytest.skip("activity_laps 테이블 없음")
        if cnt == 0:
            pytest.skip("activity_laps 데이터 없음")
        return cnt

    def test_laps_table_has_data(self, has_laps):
        assert has_laps > 0

    def test_lap_distance_m_range(self, real_conn, has_laps):
        row = real_conn.execute(
            "SELECT MIN(distance_m) AS mn, MAX(distance_m) AS mx "
            "FROM activity_laps WHERE distance_m IS NOT NULL"
        ).fetchone()
        if row["mn"] is None:
            pytest.skip("laps distance_m 없음")
        assert 0 <= row["mn"]
        assert row["mx"] <= 200_000, f"lap distance_m max={row['mx']}"

    def test_lap_duration_sec_range(self, real_conn, has_laps):
        row = real_conn.execute(
            "SELECT MIN(duration_sec) AS mn, MAX(duration_sec) AS mx "
            "FROM activity_laps WHERE duration_sec IS NOT NULL"
        ).fetchone()
        if row["mn"] is None:
            pytest.skip("laps duration_sec 없음")
        assert 0 <= row["mn"]
        assert row["mx"] <= 86400, f"lap duration_sec max={row['mx']}"

    def test_lap_avg_hr_range(self, real_conn, has_laps):
        row = real_conn.execute(
            "SELECT MIN(avg_hr) AS mn, MAX(avg_hr) AS mx "
            "FROM activity_laps WHERE avg_hr IS NOT NULL"
        ).fetchone()
        if row["mn"] is None:
            pytest.skip("laps avg_hr 없음")
        assert _HR_MIN <= row["mn"], f"lap avg_hr min={row['mn']}"
        assert row["mx"] <= _HR_MAX, f"lap avg_hr max={row['mx']}"

    def test_lap_avg_pace_running(self, real_conn, has_laps):
        row = real_conn.execute("""
            SELECT MIN(l.avg_pace_sec_km) AS mn, MAX(l.avg_pace_sec_km) AS mx
            FROM activity_laps l
            JOIN activity_summaries a ON l.activity_id = a.id
            WHERE a.activity_type IN ('running','run','virtualrun','treadmill')
              AND l.avg_pace_sec_km IS NOT NULL AND l.avg_pace_sec_km > 0
        """).fetchone()
        if row["mn"] is None:
            pytest.skip("running laps avg_pace_sec_km 없음")
        assert _PACE_MIN <= row["mn"], f"lap pace min={row['mn']}"
        assert row["mx"] <= _PACE_MAX, f"lap pace max={row['mx']}"


class TestAllBestEffortsRanges:
    """activity_best_efforts 핵심 컬럼 범위 검증."""

    @pytest.fixture(scope="class")
    def has_efforts(self, real_conn):
        try:
            cnt = real_conn.execute(
                "SELECT COUNT(*) AS n FROM activity_best_efforts"
            ).fetchone()["n"]
        except Exception:
            pytest.skip("activity_best_efforts 테이블 없음")
        if cnt == 0:
            pytest.skip("activity_best_efforts 데이터 없음")
        return cnt

    def test_efforts_table_has_data(self, has_efforts):
        assert has_efforts > 0

    def test_effort_distance_m_range(self, real_conn, has_efforts):
        row = real_conn.execute(
            "SELECT MIN(distance_m) AS mn, MAX(distance_m) AS mx "
            "FROM activity_best_efforts WHERE distance_m IS NOT NULL"
        ).fetchone()
        if row["mn"] is None:
            pytest.skip("efforts distance_m 없음")
        assert 0 < row["mn"]
        assert row["mx"] <= 200_000, f"effort distance_m max={row['mx']}"

    def test_effort_elapsed_time_range(self, real_conn, has_efforts):
        row = real_conn.execute(
            "SELECT MIN(elapsed_sec) AS mn, MAX(elapsed_sec) AS mx "
            "FROM activity_best_efforts WHERE elapsed_sec IS NOT NULL"
        ).fetchone()
        if row["mn"] is None:
            pytest.skip("efforts elapsed_sec 없음")
        assert 0 < row["mn"]
        assert row["mx"] <= 86400, f"effort elapsed_sec max={row['mx']}"

    def test_effort_implied_pace_running(self, real_conn, has_efforts):
        rows = real_conn.execute("""
            SELECT e.distance_m, e.elapsed_sec
            FROM activity_best_efforts e
            JOIN activity_summaries a ON e.activity_id = a.id
            WHERE a.activity_type IN ('running','run','virtualrun','treadmill')
              AND e.distance_m IS NOT NULL AND e.elapsed_sec IS NOT NULL
              AND e.distance_m > 0
        """).fetchall()
        if not rows:
            pytest.skip("running best_efforts 없음")
        for r in rows:
            pace = r["elapsed_sec"] / (r["distance_m"] / 1000.0)
            assert _PACE_MIN <= pace <= _PACE_MAX, (
                f"implied pace={pace:.1f}sec/km "
                f"(dist={r['distance_m']}m, time={r['elapsed_sec']}s)"
            )
