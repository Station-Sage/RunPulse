"""Phase 4 DoD (Definition of Done) 검증 테스트 — 설계서 4-8 기준."""
import sqlite3
import json
import pytest
from datetime import datetime, timedelta

from src.db_setup import create_tables
from src.metrics.engine import (
    ALL_CALCULATORS, _topological_sort,
    run_activity_metrics, run_daily_metrics, run_for_date,
    recompute_recent, recompute_all, clear_runpulse_metrics,
)
from src.utils.db_helpers import upsert_metric


def _conn():
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys=ON")
    create_tables(conn)
    return conn


def _seed_full(conn, base_date="2026-04-01", days=50):
    """50일치 활동 + wellness + TRIMP 시드."""
    target = datetime.strptime(base_date, "%Y-%m-%d")
    for i in range(days):
        d = target - timedelta(days=i)
        ds = d.strftime("%Y-%m-%d")
        conn.execute(
            "INSERT INTO activity_summaries "
            "(source, source_id, name, activity_type, start_time, "
            "distance_m, moving_time_sec, avg_hr, max_hr, avg_speed_ms) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            ["garmin", f"a{i}", "Run", "running",
             f"{ds} 08:00:00", 10000, 3000, 155, 185, 3.33],
        )
        aid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        trimp_val = 80.0 + (i % 7) * 10
        upsert_metric(conn, "activity", str(aid), "trimp",
                       "runpulse:formula_v1", numeric_value=trimp_val,
                       category="rp_load")
        conn.execute(
            "INSERT INTO daily_wellness (date, resting_hr, body_battery_high, sleep_score) "
            "VALUES (?, ?, ?, ?)", [ds, 52, 80, 85],
        )
    conn.commit()


# ── DoD #1: ALL_CALCULATORS에 19개 등록 ──
class TestDoD1:
    def test_19_calculators(self):
        assert len(ALL_CALCULATORS) >= 19

    def test_calculator_names(self):
        names = {c.name for c in ALL_CALCULATORS}
        expected = {
            "trimp", "hrss", "aerobic_decoupling_rp", "gap_rp",
            "workout_type", "runpulse_vdot", "efficiency_factor_rp", "fearp",
            "ctl", "acwr", "lsi", "monotony",
            "utrs", "cirs", "di", "darp", "tids", "rmr", "adti",
        }
        core_19 = {
            "trimp", "hrss", "aerobic_decoupling_rp", "gap_rp",
            "workout_type", "runpulse_vdot", "efficiency_factor_rp",
            "fearp", "ctl", "acwr", "lsi", "monotony",
            "utrs", "cirs", "di", "darp", "tids", "rmr", "adti",
        }
        assert core_19.issubset(names), f'Missing: {core_19 - names}'


# ── DoD #2: topological sort ──
class TestDoD2:
    def test_full_chain(self):
        sorted_calcs = _topological_sort(ALL_CALCULATORS)
        names = [c.name for c in sorted_calcs]
        assert names.index("trimp") < names.index("ctl")
        assert names.index("ctl") < names.index("acwr")
        assert names.index("acwr") < names.index("cirs")


# ── DoD #3: recompute_recent 에러 없이 완료 ──
class TestDoD3:
    def test_recompute_recent_no_error(self):
        conn = _conn()
        _seed_full(conn, days=10)
        results = recompute_recent(conn, days=3)
        assert isinstance(results, dict)
        assert len(results) == 3
        for date_key, day_result in results.items():
            assert "activity_metrics" in day_result
            assert "daily" in day_result


# ── DoD #4: metric_store에 runpulse% provider 행 존재 ──
class TestDoD4:
    def test_runpulse_provider_exists(self):
        conn = _conn()
        _seed_full(conn, days=10)
        run_for_date(conn, "2026-04-01")
        conn.commit()
        count = conn.execute(
            "SELECT COUNT(*) FROM metric_store WHERE provider LIKE 'runpulse%'"
        ).fetchone()[0]
        assert count > 0


# ── DoD #5: activity당 최소 trimp, workout_type, ef 3개 ──
class TestDoD5:
    def test_min_3_metrics_per_activity(self):
        conn = _conn()
        conn.execute(
            "INSERT INTO activity_summaries "
            "(source, source_id, name, activity_type, start_time, "
            "distance_m, moving_time_sec, avg_hr, max_hr, avg_speed_ms) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            ["garmin", "1", "Run", "running", "2026-04-01 08:00:00",
             10000, 3000, 155, 185, 3.33],
        )
        conn.execute(
            "INSERT INTO daily_wellness (date, resting_hr) VALUES (?, ?)",
            ["2026-04-01", 52],
        )
        conn.commit()
        results = run_activity_metrics(conn, 1)
        required = {"trimp", "workout_type", "efficiency_factor_rp"}
        assert required.issubset(set(results.keys())), \
            f"Missing: {required - set(results.keys())}, got: {set(results.keys())}"


# ── DoD #6: date당 최소 CTL, ATL, TSB, UTRS 4개 ──
class TestDoD6:
    def test_min_4_daily_metrics(self):
        conn = _conn()
        _seed_full(conn, days=50)
        # activity metrics 먼저 실행 (TRIMP 저장)
        acts = conn.execute(
            "SELECT id FROM activity_summaries "
            "WHERE substr(start_time,1,10)='2026-04-01'"
        ).fetchall()
        for (aid,) in acts:
            run_activity_metrics(conn, aid)
        conn.commit()
        results = run_daily_metrics(conn, "2026-04-01")
        required = {"ctl", "atl", "tsb", "utrs"}
        assert required.issubset(set(results.keys())), \
            f"Missing: {required - set(results.keys())}, got: {set(results.keys())}"


# ── DoD #7: clear → recompute_all 동일 결과 재현 ──
class TestDoD7:
    def test_idempotent_recompute(self):
        conn = _conn()
        _seed_full(conn, days=10)
        # 첫 번째 계산
        first = recompute_all(conn, days=7)
        first_count = conn.execute(
            "SELECT COUNT(*) FROM metric_store WHERE provider LIKE 'runpulse%'"
        ).fetchone()[0]
        # clear → 재계산
        clear_runpulse_metrics(conn)
        second = recompute_all(conn, days=7)
        second_count = conn.execute(
            "SELECT COUNT(*) FROM metric_store WHERE provider LIKE 'runpulse%'"
        ).fetchone()[0]
        assert first_count == second_count
        # 날짜별 키 일치
        assert set(first.keys()) == set(second.keys())


# ── DoD #8: clear_runpulse가 소스 메트릭 미영향 (기존 테스트 보강) ──
class TestDoD8:
    def test_source_metrics_preserved(self):
        conn = _conn()
        _seed_full(conn, days=5)
        # 소스 메트릭 추가
        upsert_metric(conn, "activity", "1", "vo2max", "garmin",
                       numeric_value=52.0, category="fitness")
        upsert_metric(conn, "activity", "1", "training_load", "strava",
                       numeric_value=120.0, category="load")
        conn.commit()
        run_for_date(conn, "2026-04-01")
        conn.commit()
        garmin_before = conn.execute(
            "SELECT COUNT(*) FROM metric_store WHERE provider='garmin'"
        ).fetchone()[0]
        strava_before = conn.execute(
            "SELECT COUNT(*) FROM metric_store WHERE provider='strava'"
        ).fetchone()[0]
        clear_runpulse_metrics(conn)
        garmin_after = conn.execute(
            "SELECT COUNT(*) FROM metric_store WHERE provider='garmin'"
        ).fetchone()[0]
        strava_after = conn.execute(
            "SELECT COUNT(*) FROM metric_store WHERE provider='strava'"
        ).fetchone()[0]
        assert garmin_before == garmin_after
        assert strava_before == strava_after


# ── DoD #9: confidence 필드 (UTRS, CIRS, FEARP) ──
class TestDoD9:
    def test_utrs_confidence(self):
        conn = _conn()
        conn.execute(
            "INSERT INTO daily_wellness (date, body_battery_high, sleep_score, resting_hr) "
            "VALUES (?, ?, ?, ?)", ["2026-04-01", 80, 85, 52])
        upsert_metric(conn, "daily", "2026-04-01", "tsb",
                       "runpulse:formula_v1", numeric_value=5.0, category="rp_load")
        conn.commit()
        from src.metrics.utrs import UTRSCalculator
        ctx = __import__("src.metrics.base", fromlist=["CalcContext"]).CalcContext(
            conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = UTRSCalculator().compute(ctx)
        assert len(results) == 1
        assert results[0].confidence is not None
        assert 0 < results[0].confidence <= 1.0

    def test_cirs_confidence(self):
        conn = _conn()
        upsert_metric(conn, "daily", "2026-04-01", "acwr",
                       "runpulse:formula_v1", numeric_value=1.4, category="rp_load")
        upsert_metric(conn, "daily", "2026-04-01", "lsi",
                       "runpulse:formula_v1", numeric_value=1.8, category="rp_load")
        conn.commit()
        from src.metrics.cirs import CIRSCalculator
        from src.metrics.base import CalcContext
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = CIRSCalculator().compute(ctx)
        assert len(results) == 1
        assert results[0].confidence is not None
        assert 0 < results[0].confidence <= 1.0

    def test_fearp_confidence(self):
        conn = _conn()
        conn.execute(
            "INSERT INTO activity_summaries "
            "(source, source_id, name, activity_type, start_time, "
            "distance_m, moving_time_sec, avg_hr, max_hr, avg_speed_ms, avg_temperature) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            ["garmin", "1", "Run", "running", "2026-04-01 08:00:00",
             10000, 3000, 155, 185, 3.33, 30.0])
        conn.commit()
        from src.metrics.fearp import FEARPCalculator
        from src.metrics.base import CalcContext
        ctx = CalcContext(conn=conn, scope_type="activity", scope_id="1")
        results = FEARPCalculator().compute(ctx)
        assert len(results) == 1
        assert results[0].confidence is not None
        assert 0 < results[0].confidence <= 1.0


# ── DoD #10: json_value (TIDS, RMR, workout_type) ──
class TestDoD10:
    def test_workout_type_json(self):
        conn = _conn()
        conn.execute(
            "INSERT INTO activity_summaries "
            "(source, source_id, name, activity_type, start_time, "
            "distance_m, moving_time_sec, avg_hr, max_hr, avg_speed_ms) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            ["garmin", "1", "Run", "running", "2026-04-01 08:00:00",
             10000, 3000, 155, 185, 3.33])
        conn.commit()
        from src.metrics.classifier import WorkoutClassifier
        from src.metrics.base import CalcContext
        ctx = CalcContext(conn=conn, scope_type="activity", scope_id="1")
        results = WorkoutClassifier().compute(ctx)
        assert len(results) == 1
        data = json.loads(results[0].json_value)
        assert "type" in data
        assert "confidence" in data

    def test_rmr_json(self):
        conn = _conn()
        conn.execute(
            "INSERT INTO daily_wellness (date, resting_hr, body_battery_high, sleep_score) "
            "VALUES (?, ?, ?, ?)", ["2026-04-01", 52, 85, 80])
        upsert_metric(conn, "daily", "2026-04-01", "tsb",
                       "runpulse:formula_v1", numeric_value=5.0, category="rp_load")
        conn.commit()
        from src.metrics.rmr import RMRCalculator
        from src.metrics.base import CalcContext
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = RMRCalculator().compute(ctx)
        assert len(results) == 1
        assert results[0].json_value is not None
        if isinstance(results[0].json_value, str):
            data = json.loads(results[0].json_value)
        else:
            data = results[0].json_value
        assert isinstance(data, dict)

    def test_tids_json(self):
        conn = _conn()
        _seed_full(conn, days=50)
        # workout_type 생성
        acts = conn.execute("SELECT id FROM activity_summaries").fetchall()
        from src.metrics.classifier import WorkoutClassifier
        from src.metrics.base import CalcContext
        for (aid,) in acts:
            ctx = CalcContext(conn=conn, scope_type="activity", scope_id=str(aid))
            WorkoutClassifier().compute(ctx)
            # workout_type 결과를 metric_store에 저장
            results = WorkoutClassifier().compute(ctx)
            for r in results:
                if not r.is_empty():
                    upsert_metric(conn, r.scope_type, str(aid), r.metric_name,
                                   "runpulse:rule_v1",
                                   text_value=json.loads(r.json_value)["type"] if r.json_value else None,
                                   json_value=json.loads(r.json_value) if r.json_value else None,
                                   category=r.category)
        conn.commit()
        from src.metrics.tids import TIDSCalculator
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = TIDSCalculator().compute(ctx)
        assert len(results) == 1
        assert results[0].json_value is not None
        if isinstance(results[0].json_value, str):
            data = json.loads(results[0].json_value)
        else:
            data = results[0].json_value
        assert "pattern" in data
