"""TRIMP + HRSS calculator 테스트 — 설계서 4-2 기준."""
import sqlite3
import pytest
from src.db_setup import create_tables
from src.metrics.base import CalcContext
from src.metrics.trimp import TRIMPCalculator
from src.metrics.hrss import HRSSCalculator


def _conn():
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys=ON")
    create_tables(conn)
    return conn


def _seed_activity(conn, **overrides):
    defaults = {
        "source": "garmin", "source_id": "1", "name": "Test Run",
        "activity_type": "running", "start_time": "2026-04-01 08:00:00",
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


class TestTRIMPCalculator:
    def test_compute(self):
        conn = _conn()
        aid = _seed_activity(conn)
        ctx = CalcContext(conn=conn, scope_type="activity", scope_id=str(aid))
        results = TRIMPCalculator().compute(ctx)
        assert len(results) == 1
        assert results[0].metric_name == "trimp"
        assert results[0].numeric_value > 0
        assert results[0].category == "rp_load"

    def test_no_hr(self):
        conn = _conn()
        aid = _seed_activity(conn, avg_hr=None)
        ctx = CalcContext(conn=conn, scope_type="activity", scope_id=str(aid))
        assert TRIMPCalculator().compute(ctx) == []

    def test_uses_wellness_rest_hr(self):
        conn = _conn()
        aid = _seed_activity(conn)
        conn.execute(
            "INSERT INTO daily_wellness (date, resting_hr) VALUES (?, ?)",
            ["2026-04-01", 52],
        )
        conn.commit()
        ctx = CalcContext(conn=conn, scope_type="activity", scope_id=str(aid))
        results = TRIMPCalculator().compute(ctx)
        assert len(results) == 1
        assert results[0].numeric_value > 0

    def test_confidence_without_measured_max(self):
        conn = _conn()
        aid = _seed_activity(conn)
        ctx = CalcContext(conn=conn, scope_type="activity", scope_id=str(aid))
        results = TRIMPCalculator().compute(ctx)
        assert results[0].confidence == 0.8  # 측정값 없으면 -0.2


class TestHRSSCalculator:
    def test_compute(self):
        conn = _conn()
        aid = _seed_activity(conn)
        from src.utils.db_helpers import upsert_metric
        upsert_metric(conn, "activity", str(aid), "trimp", "runpulse:formula_v1",
                       numeric_value=100.0, category="rp_load")
        conn.commit()
        ctx = CalcContext(conn=conn, scope_type="activity", scope_id=str(aid))
        results = HRSSCalculator().compute(ctx)
        assert len(results) == 1
        assert results[0].metric_name == "hrss"
        assert results[0].numeric_value > 0

    def test_no_trimp(self):
        conn = _conn()
        aid = _seed_activity(conn)
        ctx = CalcContext(conn=conn, scope_type="activity", scope_id=str(aid))
        assert HRSSCalculator().compute(ctx) == []
