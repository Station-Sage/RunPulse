"""Metrics Engine 통합 테스트."""
import sqlite3, pytest
from src.db_setup import create_tables
from src.metrics.engine import (
    ALL_CALCULATORS, _topological_sort, run_activity_metrics,
    run_daily_metrics, run_for_date, clear_runpulse_metrics,
)
from src.utils.db_helpers import upsert_metric


def _conn():
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys=ON")
    create_tables(conn)
    return conn


def _seed_full(conn):
    """활동 + wellness 시드."""
    conn.execute(
        "INSERT INTO activity_summaries "
        "(source, source_id, name, activity_type, start_time, "
        "distance_m, moving_time_sec, avg_hr, max_hr, avg_speed_ms) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        ["garmin", "1", "Morning Run", "running", "2026-04-01 08:00:00",
         10000, 3000, 155, 185, 3.33])
    conn.execute(
        "INSERT INTO daily_wellness (date, resting_hr, body_battery_high, sleep_score) "
        "VALUES (?, ?, ?, ?)", ["2026-04-01", 52, 80, 85])
    conn.commit()


class TestTopologicalSort:
    def test_trimp_before_hrss(self):
        sorted_calcs = _topological_sort(ALL_CALCULATORS)
        names = [c.name for c in sorted_calcs]
        assert names.index("trimp") < names.index("hrss")

    def test_pmc_before_acwr(self):
        sorted_calcs = _topological_sort(ALL_CALCULATORS)
        names = [c.name for c in sorted_calcs]
        assert names.index("ctl") < names.index("acwr")

    def test_acwr_before_cirs(self):
        sorted_calcs = _topological_sort(ALL_CALCULATORS)
        names = [c.name for c in sorted_calcs]
        assert names.index("acwr") < names.index("cirs")

    def test_all_calculators_included(self):
        sorted_calcs = _topological_sort(ALL_CALCULATORS)
        assert len(sorted_calcs) == len(ALL_CALCULATORS)


class TestRunActivityMetrics:
    def test_produces_metrics(self):
        conn = _conn()
        _seed_full(conn)
        results = run_activity_metrics(conn, 1)
        assert "trimp" in results
        assert "efficiency_factor_rp" in results

    def test_metrics_in_store(self):
        conn = _conn()
        _seed_full(conn)
        run_activity_metrics(conn, 1)
        rows = conn.execute(
            "SELECT metric_name FROM metric_store "
            "WHERE scope_type='activity' AND scope_id='1' AND is_primary=1"
        ).fetchall()
        names = {r[0] for r in rows}
        assert "trimp" in names


class TestRunDailyMetrics:
    def test_with_trimp(self):
        conn = _conn()
        _seed_full(conn)
        # 먼저 activity metrics 실행 (TRIMP 필요)
        run_activity_metrics(conn, 1)
        conn.commit()
        results = run_daily_metrics(conn, "2026-04-01")
        # PMC는 최소 1개 TRIMP가 있으면 동작
        assert len(results) > 0


class TestRunForDate:
    def test_full_pipeline(self):
        conn = _conn()
        _seed_full(conn)
        results = run_for_date(conn, "2026-04-01")
        assert "activity_metrics" in results
        assert "daily" in results
        assert 1 in results["activity_metrics"]


class TestClearRunpulse:
    def test_clears_only_runpulse(self):
        conn = _conn()
        _seed_full(conn)
        # 소스 메트릭
        upsert_metric(conn, "activity", "1", "vo2max", "garmin",
                       numeric_value=52.0, category="fitness")
        # RunPulse 메트릭
        run_activity_metrics(conn, 1)
        conn.commit()

        before = conn.execute("SELECT COUNT(*) FROM metric_store").fetchone()[0]
        deleted = clear_runpulse_metrics(conn)
        after = conn.execute("SELECT COUNT(*) FROM metric_store").fetchone()[0]

        assert deleted > 0
        assert after < before
        # garmin 메트릭은 남아있어야 함
        garmin = conn.execute(
            "SELECT COUNT(*) FROM metric_store WHERE provider='garmin'"
        ).fetchone()[0]
        assert garmin == 1
