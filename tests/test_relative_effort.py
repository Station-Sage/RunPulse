import sqlite3
import json
import pytest
from src.db_setup import create_tables
from src.utils.db_helpers import upsert_metric
from src.metrics.base import CalcContext
from src.metrics.relative_effort import RelativeEffortCalculator

def _conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    create_tables(conn)
    return conn


def _seed_activity(conn, act_date="2026-04-01", **overrides):
    defaults = {
        "source": "garmin", "source_id": "1", "name": "Test Run",
        "activity_type": "running", "start_time": f"{act_date} 08:00:00",
        "distance_m": 10000, "moving_time_sec": 3000,
        "avg_hr": 155, "max_hr": 185,
    }
    defaults.update(overrides)
    cols = ", ".join(defaults.keys())
    vals = ", ".join("?" * len(defaults))
    conn.execute(f"INSERT INTO activity_summaries ({cols}) VALUES ({vals})",
                 list(defaults.values()))
    conn.commit()
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def _seed_wellness(conn, d="2026-04-01", **overrides):
    defaults = {"date": d, "resting_hr": 55}
    defaults.update(overrides)
    cols = ", ".join(defaults.keys())
    vals = ", ".join("?" * len(defaults))
    conn.execute(f"INSERT OR REPLACE INTO daily_wellness ({cols}) VALUES ({vals})",
                 list(defaults.values()))
    conn.commit()


def _seed_daily_metrics(conn, d, **metrics):
    for name, val in metrics.items():
        upsert_metric(conn, "daily", d, name, "runpulse:formula_v1",
                      numeric_value=val, category="rp_load")


class TestRelativeEffort:
    def test_from_avg_hr(self):
        conn = _conn()
        aid = _seed_activity(conn, avg_hr=155, max_hr=185)
        ctx = CalcContext(conn=conn, scope_type="activity", scope_id=str(aid))
        results = RelativeEffortCalculator().compute(ctx)
        assert len(results) == 1
        assert results[0].metric_name == "relative_effort"
        assert results[0].numeric_value > 0

    def test_high_intensity(self):
        conn = _conn()
        aid = _seed_activity(conn, avg_hr=175, max_hr=185, moving_time_sec=3600)
        ctx = CalcContext(conn=conn, scope_type="activity", scope_id=str(aid))
        results = RelativeEffortCalculator().compute(ctx)
        assert results[0].numeric_value > 100

    def test_low_intensity(self):
        conn = _conn()
        aid = _seed_activity(conn, avg_hr=100, max_hr=185, moving_time_sec=3600)
        ctx = CalcContext(conn=conn, scope_type="activity", scope_id=str(aid))
        results = RelativeEffortCalculator().compute(ctx)
        assert results[0].numeric_value < 100

    def test_no_hr(self):
        conn = _conn()
        aid = _seed_activity(conn, avg_hr=None, max_hr=None)
        ctx = CalcContext(conn=conn, scope_type="activity", scope_id=str(aid))
        results = RelativeEffortCalculator().compute(ctx)
        assert len(results) == 0

    def test_confidence_from_avg_hr(self):
        conn = _conn()
        aid = _seed_activity(conn)
        ctx = CalcContext(conn=conn, scope_type="activity", scope_id=str(aid))
        results = RelativeEffortCalculator().compute(ctx)
        assert results[0].confidence == 0.6

    def test_category(self):
        conn = _conn()
        aid = _seed_activity(conn)
        ctx = CalcContext(conn=conn, scope_type="activity", scope_id=str(aid))
        results = RelativeEffortCalculator().compute(ctx)
        assert results[0].category == "rp_load"

# ══════════════════════════════════════════
# Mock 테스트 (보강 #5)
# ══════════════════════════════════════════
from tests.helpers.mock_context import MockCalcContext


class TestRelativeEffortMock:
    def test_basic_mock(self):
        ctx = MockCalcContext(
            activity_data={
                "avg_hr": 155, "max_hr": 185,
                "moving_time_sec": 3600, "activity_type": "running",
            },
        )
        results = RelativeEffortCalculator().compute(ctx)
        assert len(results) == 1
        assert results[0].numeric_value > 0

    def test_no_hr_mock(self):
        ctx = MockCalcContext(
            activity_data={"moving_time_sec": 3600, "activity_type": "running"},
        )
        assert RelativeEffortCalculator().compute(ctx) == []
