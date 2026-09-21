"""라운드 2 테스트: ComputeResult, compute_for_activities/dates, recompute_single_metric."""
import sqlite3
import pytest
from src.db_setup import create_tables
from src.utils.db_helpers import upsert_metric
from src.metrics.engine import (
    ComputeResult, compute_for_activities, compute_for_dates,
    recompute_all, recompute_single_metric, run_activity_metrics,
)


def _conn():
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys=ON")
    create_tables(conn)
    return conn


def _seed(conn, days=10):
    from datetime import datetime, timedelta
    target = datetime.now()
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
        from datetime import datetime, timedelta
        conn = _conn()
        ids = _seed(conn, days=10)
        # activity metrics 먼저 실행해서 TRIMP 생성
        for aid in ids:
            run_activity_metrics(conn, aid)
        conn.commit()
        today = datetime.now()
        d1 = today.strftime("%Y-%m-%d")
        d2 = (today - timedelta(days=1)).strftime("%Y-%m-%d")
        result = compute_for_dates(conn, [d1, d2])
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
        result = recompute_single_metric(conn, "trimp", days=30)
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


def _recent_dates(days):
    from datetime import datetime, timedelta
    today = datetime.now()
    return [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days)]


class TestComputeForDatesRunsActivityMetrics:
    """daily calculator는 활동 TRIMP에 의존하므로 같은 호출에서 함께 계산돼야 한다."""

    def test_trimp_is_computed(self):
        conn = _conn()
        _seed(conn, days=3)
        compute_for_dates(conn, _recent_dates(3))
        count = conn.execute(
            "SELECT COUNT(*) FROM metric_store "
            "WHERE scope_type='activity' AND metric_name='trimp'"
        ).fetchone()[0]
        assert count == 3

    def test_trimp_is_marked_primary(self):
        """prefetch가 is_primary=1만 읽으므로 primary까지 확정돼야 한다."""
        conn = _conn()
        _seed(conn, days=3)
        compute_for_dates(conn, _recent_dates(3))
        count = conn.execute(
            "SELECT COUNT(*) FROM metric_store WHERE scope_type='activity' "
            "AND metric_name='trimp' AND is_primary=1"
        ).fetchone()[0]
        assert count == 3

    def test_ctl_reflects_trimp_from_same_call(self):
        """회귀: 활동 메트릭을 prefetch 이후에 계산하면 CTL이 0이 되거나 생성되지 않는다."""
        conn = _conn()
        _seed(conn, days=3)
        compute_for_dates(conn, _recent_dates(3))
        row = conn.execute(
            "SELECT numeric_value FROM metric_store "
            "WHERE scope_type='daily' AND metric_name='ctl' ORDER BY scope_id DESC LIMIT 1"
        ).fetchone()
        assert row is not None, "CTL이 생성되지 않음 — TRIMP가 그날 부하에 반영되지 않았다"
        assert row[0] > 0, f"CTL={row[0]} — prefetch가 새 TRIMP를 읽지 못했다"

    def test_no_activities_still_runs_daily(self):
        conn = _conn()
        result = compute_for_dates(conn, _recent_dates(2))
        assert result.total_scopes == 2


class TestRecomputeAll:
    def test_ctl_recomputed_after_clear(self):
        conn = _conn()
        _seed(conn, days=3)
        results = recompute_all(conn, days=3)
        assert all("activity_metrics" in r and "daily" in r for r in results.values())
        row = conn.execute(
            "SELECT numeric_value FROM metric_store "
            "WHERE scope_type='daily' AND metric_name='ctl' ORDER BY scope_id DESC LIMIT 1"
        ).fetchone()
        assert row is not None and row[0] > 0

    def test_on_progress_callback(self):
        """UI 재계산 화면이 진행률 콜백을 넘긴다."""
        conn = _conn()
        _seed(conn, days=2)
        calls = []
        recompute_all(conn, days=2, on_progress=lambda d, done, total: calls.append((d, done, total)))
        assert [c[1] for c in calls] == [1, 2]
        assert calls[-1][2] == 2
