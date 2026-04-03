"""라운드 2 테스트: ComputeResult, compute_for_activities/dates, recompute_single_metric, integration."""
import sqlite3
import pytest
from src.db_setup import create_tables
from src.utils.db_helpers import upsert_metric
from src.metrics.engine import (
    ComputeResult, compute_for_activities, compute_for_dates,
    recompute_single_metric, run_activity_metrics,
)


def _conn():
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys=ON")
    create_tables(conn)
    return conn


def _seed(conn, days=10):
    from datetime import datetime, timedelta
    target = datetime(2026, 4, 1)
    ids = []
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
        ids.append(aid)
        conn.execute(
            "INSERT INTO daily_wellness (date, resting_hr, body_battery_high, sleep_score) "
            "VALUES (?, ?, ?, ?)", [ds, 52, 80, 85])
    conn.commit()
    return ids


class TestComputeResult:
    def test_summary(self):
        r = ComputeResult(computed_count=5, skipped_count=2, error_count=1, elapsed_seconds=1.23)
        s = r.summary()
        assert "Computed: 5" in s
        assert "Skipped: 2" in s
        assert "Errors: 1" in s

    def test_defaults(self):
        r = ComputeResult()
        assert r.computed_count == 0
        assert r.errors == []


class TestComputeForActivities:
    def test_basic(self):
        conn = _conn()
        ids = _seed(conn, days=3)
        result = compute_for_activities(conn, ids[:2])
        assert isinstance(result, ComputeResult)
        assert result.total_scopes == 2
        assert result.computed_count > 0
        assert result.elapsed_seconds >= 0

    def test_empty_list(self):
        conn = _conn()
        result = compute_for_activities(conn, [])
        assert result.total_scopes == 0


class TestComputeForDates:
    def test_basic(self):
        conn = _conn()
        ids = _seed(conn, days=10)
        # activity metrics 먼저 실행해서 TRIMP 생성
        for aid in ids:
            run_activity_metrics(conn, aid)
        conn.commit()
        result = compute_for_dates(conn, ["2026-04-01", "2026-03-31"])
        assert isinstance(result, ComputeResult)
        assert result.total_scopes == 2
        assert result.computed_count > 0

    def test_empty_dates(self):
        conn = _conn()
        result = compute_for_dates(conn, [])
        assert result.total_scopes == 0


class TestRecomputeSingleMetric:
    def test_trimp(self):
        conn = _conn()
        ids = _seed(conn, days=5)
        # 먼저 전체 계산
        for aid in ids:
            run_activity_metrics(conn, aid)
        conn.commit()

        before = conn.execute(
            "SELECT COUNT(*) FROM metric_store WHERE metric_name='trimp'"
        ).fetchone()[0]
        assert before > 0

        # trimp만 재계산
        result = recompute_single_metric(conn, "trimp", days=10)
        assert isinstance(result, ComputeResult)
        assert result.computed_count > 0

        after = conn.execute(
            "SELECT COUNT(*) FROM metric_store WHERE metric_name='trimp'"
        ).fetchone()[0]
        assert after == before

    def test_invalid_metric(self):
        conn = _conn()
        with pytest.raises(ValueError, match="No calculator"):
            recompute_single_metric(conn, "nonexistent_metric")


class TestIntegration:
    def test_compute_metrics_after_sync(self):
        conn = _conn()
        ids = _seed(conn, days=5)
        from src.sync.integration import compute_metrics_after_sync
        results = compute_metrics_after_sync(conn, ids[:2])
        assert "activity_result" in results
        assert "daily_result" in results
        assert results["activity_result"].computed_count > 0
