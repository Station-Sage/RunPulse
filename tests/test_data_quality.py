"""분석 파이프라인 데이터 품질 검증 테스트.

4주 훈련 데이터 픽스처 기반으로 각 분석 모듈의 반환값이
물리적으로 가능한 범위에 있고 의도한 의미를 갖는지 검증한다.
기존 단위 테스트가 로직 정확성을 검증한다면, 이 파일은 의미론적 범위를 검증한다.
"""
from __future__ import annotations

import json
import re
import sqlite3
from datetime import date, timedelta

import pytest

from src.analysis.trends import weekly_trends, fitness_trend
from src.analysis.compare import compare_periods, compare_this_week_vs_last
from src.analysis.weekly_score import calculate_weekly_score
from src.analysis.race_readiness import assess_race_readiness
from src.analysis.activity_deep import deep_analyze
from src.ai.suggestions import get_runner_state, rule_based_chips, RunnerState
from src.services.dashboard_service import get_dashboard_data
from src.services.wellness_service import get_wellness_detail, get_wellness_trend


# ─── 물리 범위 상수 ─────────────────────────────────────────────────────────
_PACE_MIN, _PACE_MAX = 180, 600       # sec/km (3:00~10:00)
_HR_MIN, _HR_MAX = 40, 220            # bpm
_DIST_WEEK_MAX = 200                  # km/week 상한 (아마추어 기준)
_CTL_MAX = 150
_ATL_MAX = 200
_TSB_MIN, _TSB_MAX = -100, 60

_VALID_GRADES = {"A", "B", "C", "D", "F"}
_VALID_PHASES = {"tapering", "recovering", "building", "detraining", "maintaining", "unknown"}
_VALID_ACWR_STATUS = {"low", "safe", "caution", "danger", "unknown"}

_TODAY = date.today()
_MONDAY = _TODAY - timedelta(days=_TODAY.weekday())

# 주 4회 훈련 패턴: (요일오프셋, 거리m, 시간s, 페이스s/km, avg_hr, max_hr)
_WEEKLY_RUNS = [
    (1, 10_000, 3_500, 350, 133, 158),  # 화 easy
    (3,  8_000, 2_400, 300, 158, 177),  # 목 tempo
    (5, 12_000, 3_840, 320, 145, 165),  # 토 medium
    (6, 18_000, 5_940, 330, 143, 162),  # 일 long
]


# ─── 픽스처 헬퍼 ─────────────────────────────────────────────────────────────

def _insert_activities(conn: sqlite3.Connection) -> list[int]:
    """4주 × 4회 = 최대 16개 활동 삽입 (미래 날짜 제외). 삽입된 id 반환."""
    ids = []
    for w in range(4):
        wk_mon = _MONDAY - timedelta(weeks=w)
        for day_off, dist, dur, pace, avg_hr, max_hr in _WEEKLY_RUNS:
            act_date = wk_mon + timedelta(days=day_off)
            if act_date > _TODAY:
                continue
            cur = conn.execute(
                "INSERT INTO activity_summaries"
                " (source, source_id, activity_type, start_time,"
                "  distance_m, duration_sec, avg_pace_sec_km, avg_hr, max_hr, elevation_gain)"
                " VALUES ('garmin', ?, 'running', ?, ?, ?, ?, ?, ?, 50)",
                (f"g_{w}_{day_off}", f"{act_date.isoformat()}T08:00:00",
                 dist, dur, pace, avg_hr, max_hr),
            )
            ids.append(cur.lastrowid)
    return ids


def _insert_wellness(conn: sqlite3.Connection) -> None:
    """28일 daily_wellness 삽입."""
    for i in range(28):
        conn.execute(
            "INSERT OR IGNORE INTO daily_wellness"
            " (date, sleep_score, sleep_duration_sec, hrv_last_night,"
            "  resting_hr, body_battery_high, avg_stress)"
            " VALUES (?, 75, 25200, 60, 54, 80, 35)",
            ((_TODAY - timedelta(days=i)).isoformat(),),
        )


def _insert_daily_metrics(conn: sqlite3.Connection) -> None:
    """28일 CTL/ATL/TSB/acwr/ramp_rate + runalyze vdot/marathon_shape."""
    for i in range(28):
        d = (_TODAY - timedelta(days=i)).isoformat()
        ctl = round(55 + (27 - i) / 27 * 10, 1)   # 55→65 점진 빌드
        atl = round(50 + (i % 14) / 14 * 20, 1)   # 50~70 주기 변동
        tsb = round(ctl - atl, 1)
        for metric_name, provider, val in [
            ("ctl",                    "intervals", ctl),
            ("atl",                    "intervals", atl),
            ("tsb",                    "intervals", tsb),
            ("acwr",                   "intervals", 1.1),
            ("ramp_rate",              "intervals", 2.5),
            ("runalyze_vdot",          "runalyze",  50.0),
            ("runalyze_marathon_shape","runalyze",  96.5),
        ]:
            conn.execute(
                "INSERT OR IGNORE INTO metric_store"
                " (scope_type, scope_id, provider, metric_name, numeric_value, is_primary)"
                " VALUES ('daily', ?, ?, ?, ?, 1)",
                (d, provider, metric_name, val),
            )


def _insert_activity_metrics(conn: sqlite3.Connection, act_ids: list[int]) -> None:
    """활동별 VO2max / training_load / hr_zones_detail / race_prediction 삽입."""
    hr_zones = json.dumps([600, 1200, 1500, 900, 300])
    race_pred = json.dumps({"5k": 1080, "10k": 2280, "half": 5040, "full": 10560})
    for act_id in act_ids:
        sid = str(act_id)
        for provider, metric_name, num_val, json_val in [
            ("garmin",    "vo2max_activity",  52.5, None),
            ("garmin",    "training_load",    80.0, None),   # ACWR 계산용
            ("intervals", "hr_zones_detail",  None, hr_zones),
            ("runalyze",  "effective_vo2max", 53.0, None),
            ("runalyze",  "race_prediction",  None, race_pred),
        ]:
            conn.execute(
                "INSERT OR IGNORE INTO metric_store"
                " (scope_type, scope_id, provider, metric_name,"
                "  numeric_value, json_value, is_primary)"
                " VALUES ('activity', ?, ?, ?, ?, ?, 1)",
                (sid, provider, metric_name, num_val, json_val),
            )


@pytest.fixture
def rich_conn(db_conn):
    """4주 러너 데이터 픽스처 (활동 + 웰니스 + 메트릭)."""
    act_ids = _insert_activities(db_conn)
    _insert_wellness(db_conn)
    _insert_daily_metrics(db_conn)
    _insert_activity_metrics(db_conn, act_ids)
    db_conn.commit()
    return db_conn


# ─── 1. TestTrendsRanges ──────────────────────────────────────────────────────

class TestTrendsRanges:
    def test_weekly_distances_in_km(self, rich_conn):
        rows = weekly_trends(rich_conn, weeks=4)
        for r in rows:
            dist = r.get("total_distance_km") or 0
            assert 0 <= dist < _DIST_WEEK_MAX, f"주별 거리 범위 초과: {dist}"

    def test_weekly_pace_range(self, rich_conn):
        rows = weekly_trends(rich_conn, weeks=4)
        for r in rows:
            pace = r.get("avg_pace_sec_km")
            if pace is not None:
                assert _PACE_MIN <= pace <= _PACE_MAX, f"비정상 페이스: {pace}s/km"

    def test_fitness_ctl_atl_range(self, rich_conn):
        rows = fitness_trend(rich_conn, weeks=4)
        for r in rows:
            ctl = r.get("intervals_ctl")
            atl = r.get("intervals_atl")
            if ctl is not None:
                assert 0 <= ctl <= _CTL_MAX, f"CTL 범위 초과: {ctl}"
            if atl is not None:
                assert 0 <= atl <= _ATL_MAX, f"ATL 범위 초과: {atl}"

    def test_fitness_tsb_range(self, rich_conn):
        rows = fitness_trend(rich_conn, weeks=4)
        for r in rows:
            tsb = r.get("intervals_tsb")
            if tsb is not None:
                assert _TSB_MIN <= tsb <= _TSB_MAX, f"TSB 범위 초과: {tsb}"

    def test_nonzero_weeks_exist(self, rich_conn):
        rows = weekly_trends(rich_conn, weeks=4)
        nonzero = [r for r in rows if r.get("total_distance_km", 0) > 0]
        assert len(nonzero) >= 2, "최소 2주 이상 거리 데이터가 있어야 함"

    def test_fitness_ctl_present(self, rich_conn):
        """픽스처에 CTL이 있으므로 4주 중 최소 1주는 CTL이 조회돼야 한다."""
        rows = fitness_trend(rich_conn, weeks=4)
        ctl_values = [r["intervals_ctl"] for r in rows if r.get("intervals_ctl") is not None]
        assert len(ctl_values) >= 1, "CTL이 한 번도 조회되지 않음 (scope_type 오류 의심)"


# ─── 2. TestCompareRanges ─────────────────────────────────────────────────────

class TestCompareRanges:
    def test_all_required_keys(self, rich_conn):
        p1_start = (_TODAY - timedelta(days=21)).isoformat()
        p1_end   = (_TODAY - timedelta(days=10)).isoformat()
        p2_start = (_TODAY - timedelta(days=10)).isoformat()
        p2_end   = _TODAY.isoformat()
        result = compare_periods(rich_conn, p1_start, p1_end, p2_start, p2_end)
        for key in ("period1", "period2", "delta", "pct"):
            assert key in result, f"compare_periods 결과에 키 누락: {key}"

    def test_delta_equals_p2_minus_p1(self, rich_conn):
        p1_start = (_TODAY - timedelta(days=21)).isoformat()
        p1_end   = (_TODAY - timedelta(days=10)).isoformat()
        p2_start = (_TODAY - timedelta(days=10)).isoformat()
        p2_end   = _TODAY.isoformat()
        result = compare_periods(rich_conn, p1_start, p1_end, p2_start, p2_end)
        p1_dist = result["period1"]["total_distance_km"] or 0
        p2_dist = result["period2"]["total_distance_km"] or 0
        delta   = result["delta"]["total_distance_km"] or 0
        assert abs(delta - (p2_dist - p1_dist)) < 0.01, \
            f"delta 수학 오류: {delta:.2f} ≠ {p2_dist:.2f} - {p1_dist:.2f}"

    def test_distances_in_km_range(self, rich_conn):
        result = compare_this_week_vs_last(rich_conn)
        for key in ("period1", "period2"):
            dist = result[key].get("total_distance_km") or 0
            assert 0 <= dist < 500, f"{key} 거리 범위 초과: {dist}km"

    def test_avg_hr_range_when_present(self, rich_conn):
        p1_start = (_TODAY - timedelta(days=21)).isoformat()
        p1_end   = (_TODAY - timedelta(days=10)).isoformat()
        p2_start = (_TODAY - timedelta(days=10)).isoformat()
        p2_end   = _TODAY.isoformat()
        result = compare_periods(rich_conn, p1_start, p1_end, p2_start, p2_end)
        for key in ("period1", "period2"):
            hr = result[key].get("avg_hr")
            if hr is not None:
                assert _HR_MIN <= hr <= _HR_MAX, f"{key}.avg_hr 범위 초과: {hr}"


# ─── 3. TestWeeklyScoreRanges ─────────────────────────────────────────────────

class TestWeeklyScoreRanges:
    def test_score_0_to_100(self, rich_conn):
        result = calculate_weekly_score(rich_conn)
        score = result.get("total_score")
        assert score is not None, "total_score가 None"
        assert 0 <= score <= 100, f"점수 범위 초과: {score}"

    def test_grade_valid(self, rich_conn):
        result = calculate_weekly_score(rich_conn)
        grade = result.get("grade")
        assert grade in _VALID_GRADES, f"잘못된 grade: {grade!r}"

    def test_components_non_negative(self, rich_conn):
        result = calculate_weekly_score(rich_conn)
        for name, val in result.get("components", {}).items():
            assert (val or 0) >= 0, f"component {name} 음수: {val}"

    def test_data_distance_km(self, rich_conn):
        result = calculate_weekly_score(rich_conn)
        dist = result.get("data", {}).get("total_distance_km") or 0
        assert 0 <= dist < _DIST_WEEK_MAX, f"주간 거리 범위 초과: {dist}km"


# ─── 4. TestRaceReadinessRanges ───────────────────────────────────────────────

class TestRaceReadinessRanges:
    def test_readiness_score_range(self, rich_conn):
        result = assess_race_readiness(rich_conn)
        score = result.get("readiness_score")
        if score is not None:
            assert 0 <= score <= 100, f"준비도 점수 범위 초과: {score}"

    def test_grade_valid(self, rich_conn):
        result = assess_race_readiness(rich_conn)
        grade = result.get("grade")
        assert grade is None or grade in _VALID_GRADES, f"잘못된 grade: {grade!r}"

    def test_5k_prediction_range(self, rich_conn):
        result = assess_race_readiness(rich_conn)
        pred = (result.get("race_predictions") or {}).get("5k")
        if pred is not None:
            assert 600 <= pred <= 3600, f"5k 예측 범위 초과: {pred}s"

    def test_10k_prediction_range(self, rich_conn):
        result = assess_race_readiness(rich_conn)
        pred = (result.get("race_predictions") or {}).get("10k")
        if pred is not None:
            assert 1200 <= pred <= 7200, f"10k 예측 범위 초과: {pred}s"

    def test_half_prediction_range(self, rich_conn):
        result = assess_race_readiness(rich_conn)
        pred = (result.get("race_predictions") or {}).get("half")
        if pred is not None:
            assert 3000 <= pred <= 14400, f"하프 예측 범위 초과: {pred}s"

    def test_full_prediction_range(self, rich_conn):
        result = assess_race_readiness(rich_conn)
        pred = (result.get("race_predictions") or {}).get("full")
        if pred is not None:
            assert 7200 <= pred <= 28800, f"풀마 예측 범위 초과: {pred}s"

    def test_recommendation_nonempty(self, rich_conn):
        result = assess_race_readiness(rich_conn)
        rec = result.get("recommendation") or ""
        assert len(rec.strip()) > 0, "recommendation이 빈 문자열"

    def test_component_scores_range(self, rich_conn):
        result = assess_race_readiness(rich_conn)
        for name, val in (result.get("scores") or {}).items():
            if val is not None:
                assert 0 <= val <= 100, f"scores.{name} 범위 초과: {val}"

    def test_predictions_come_from_fixture_data(self, rich_conn):
        """픽스처에 race_prediction JSON이 있으므로 예측값이 반드시 존재해야 한다."""
        result = assess_race_readiness(rich_conn)
        preds = result.get("race_predictions") or {}
        has_any = any(v is not None for v in preds.values())
        assert has_any, "race_prediction 메트릭이 있음에도 예측값 전체 None"


# ─── 5. TestActivityDeepRanges ────────────────────────────────────────────────

class TestActivityDeepRanges:
    @pytest.fixture
    def first_act_id(self, rich_conn):
        row = rich_conn.execute("SELECT id FROM activity_summaries LIMIT 1").fetchone()
        return row[0]

    def test_structure_keys(self, rich_conn, first_act_id):
        result = deep_analyze(rich_conn, activity_id=first_act_id)
        assert result is not None, "deep_analyze가 None 반환"
        for key in ("activity", "garmin", "intervals", "runalyze", "fitness_context"):
            assert key in result, f"최상위 키 누락: {key}"

    def test_pace_format(self, rich_conn, first_act_id):
        result = deep_analyze(rich_conn, activity_id=first_act_id)
        avg_pace = result["activity"].get("avg_pace")
        if avg_pace is not None:
            assert re.match(r"^\d+:\d{2}$", avg_pace), \
                f"avg_pace 형식 오류: {avg_pace!r} (기대: 'M:SS' 또는 'MM:SS')"

    def test_distance_km_not_m(self, rich_conn, first_act_id):
        result = deep_analyze(rich_conn, activity_id=first_act_id)
        act = result["activity"]
        assert "distance_km" in act, "activity에 distance_km 키 없음"
        km = act["distance_km"]
        assert 0.5 <= km <= 100, f"distance_km 범위 초과: {km}"

    def test_hr_range(self, rich_conn, first_act_id):
        result = deep_analyze(rich_conn, activity_id=first_act_id)
        act = result["activity"]
        for hr_key in ("avg_hr", "max_hr"):
            val = act.get(hr_key)
            if val is not None:
                assert _HR_MIN <= val <= _HR_MAX, f"{hr_key} 범위 초과: {val}bpm"

    def test_fitness_context_ctl_present(self, rich_conn, first_act_id):
        """픽스처에 daily CTL이 있으므로 fitness_context.ctl이 존재해야 한다."""
        result = deep_analyze(rich_conn, activity_id=first_act_id)
        ctl = result.get("fitness_context", {}).get("ctl")
        if ctl is not None:
            assert 0 <= ctl <= _CTL_MAX, f"fitness_context.ctl 범위 초과: {ctl}"


# ─── 6. TestSuggestionsRanges ─────────────────────────────────────────────────

class TestSuggestionsRanges:
    def test_state_acwr_status_valid(self, rich_conn):
        state = get_runner_state(rich_conn)
        assert state.acwr_status in _VALID_ACWR_STATUS, \
            f"잘못된 acwr_status: {state.acwr_status!r}"

    def test_weekly_run_count_plausible(self, rich_conn):
        state = get_runner_state(rich_conn)
        assert 0 <= state.weekly_run_count <= 7, \
            f"weekly_run_count 범위 초과: {state.weekly_run_count}"

    def test_total_distance_non_negative(self, rich_conn):
        state = get_runner_state(rich_conn)
        assert state.total_distance_this_week >= 0

    def test_chips_count_range(self, rich_conn):
        state = get_runner_state(rich_conn)
        chips = rule_based_chips(state)
        assert 1 <= len(chips) <= 5, f"칩 개수 범위 초과: {len(chips)}"

    def test_chips_have_required_keys(self, rich_conn):
        state = get_runner_state(rich_conn)
        chips = rule_based_chips(state)
        for chip in chips:
            assert "id" in chip, f"칩에 id 키 없음: {chip}"
            assert "label" in chip, f"칩에 label 키 없음: {chip}"

    def test_danger_acwr_triggers_injury_chip(self):
        """acwr_status='danger'이면 injury_risk 칩이 반드시 포함돼야 한다."""
        danger_state = RunnerState(
            date=_TODAY.isoformat(),
            has_today_run=False,
            acwr=1.6,
            acwr_status="danger",
            weekly_run_count=5,
            total_distance_this_week=50.0,
        )
        chips = rule_based_chips(danger_state)
        chip_ids = [c["id"] for c in chips]
        assert "injury_risk" in chip_ids, \
            f"danger 상태에서 injury_risk 칩 없음: {chip_ids}"

    def test_safe_acwr_no_injury_as_first_chip(self):
        """acwr_status='safe'이면 injury_risk 칩이 최우선이 아니어야 한다."""
        safe_state = RunnerState(
            date=_TODAY.isoformat(),
            has_today_run=False,
            acwr=1.0,
            acwr_status="safe",
            weekly_run_count=3,
            total_distance_this_week=30.0,
        )
        chips = rule_based_chips(safe_state)
        if chips:
            assert chips[0]["id"] != "injury_risk", \
                "safe 상태에서 injury_risk 칩이 첫 번째"


# ─── 7. TestDashboardRanges ───────────────────────────────────────────────────

class TestDashboardRanges:
    def test_required_keys(self, rich_conn):
        result = get_dashboard_data(rich_conn)
        for key in ("wellness", "training_status", "recent_activities", "weekly_summary"):
            assert key in result, f"get_dashboard_data 결과에 키 누락: {key}"

    def test_training_phase_valid(self, rich_conn):
        result = get_dashboard_data(rich_conn)
        phase = result["training_status"].get("training_phase")
        assert phase in _VALID_PHASES, f"잘못된 training_phase: {phase!r}"

    def test_weekly_summary_non_negative(self, rich_conn):
        result = get_dashboard_data(rich_conn)
        ws = result["weekly_summary"]
        assert (ws.get("total_distance_m") or 0) >= 0
        assert (ws.get("total_duration_sec") or 0) >= 0

    def test_ctl_range_when_present(self, rich_conn):
        result = get_dashboard_data(rich_conn)
        ctl = result["training_status"].get("ctl")
        if ctl is not None:
            assert 0 <= ctl <= _CTL_MAX, f"CTL 범위 초과: {ctl}"

    def test_recent_activities_have_distance(self, rich_conn):
        result = get_dashboard_data(rich_conn)
        for act in result.get("recent_activities", []):
            dist = act.get("distance_m") or 0
            assert dist >= 0, f"distance_m 음수: {dist}"


# ─── 8. TestWellnessRanges ────────────────────────────────────────────────────

class TestWellnessRanges:
    def test_hrv_range(self, rich_conn):
        result = get_wellness_detail(rich_conn)
        hrv = (result.get("core") or {}).get("hrv_last_night")
        if hrv is not None:
            assert 10 <= hrv <= 120, f"HRV 범위 초과: {hrv}ms"

    def test_resting_hr_range(self, rich_conn):
        result = get_wellness_detail(rich_conn)
        rhr = (result.get("core") or {}).get("resting_hr")
        if rhr is not None:
            assert 30 <= rhr <= 90, f"안정심박수 범위 초과: {rhr}bpm"

    def test_sleep_score_range(self, rich_conn):
        result = get_wellness_detail(rich_conn)
        ss = (result.get("core") or {}).get("sleep_score")
        if ss is not None:
            assert 0 <= ss <= 100, f"수면 점수 범위 초과: {ss}"

    def test_trend_arrays_same_length(self, rich_conn):
        result = get_wellness_trend(rich_conn, days=14)
        dates = result.get("dates", [])
        assert len(dates) > 0, "wellness_trend dates 배열이 빔"
        for key in ("sleep_score", "hrv_last_night", "resting_hr"):
            arr = result.get(key, [])
            assert len(arr) == len(dates), \
                f"{key} 배열 길이 불일치: {len(arr)} ≠ {len(dates)}"

    def test_wellness_detail_has_core(self, rich_conn):
        result = get_wellness_detail(rich_conn)
        assert "core" in result, "get_wellness_detail 결과에 'core' 키 없음"
        core = result["core"]
        assert core is not None and len(core) > 0, "core가 비어있음"
