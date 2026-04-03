import sqlite3
import json
import pytest
from src.db_setup import create_tables
from src.utils.db_helpers import upsert_metric
from src.metrics.base import CalcContext
from src.metrics.rtti import RTTICalculator

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


class TestRTTI:
    def test_optimal(self):
        conn = _conn()
        _seed_wellness(conn, "2026-04-01", body_battery_high=80, sleep_score=85)
        _seed_daily_metrics(conn, "2026-04-01", ctl=50.0, atl=50.0)
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = RTTICalculator().compute(ctx)
        assert len(results) == 1
        assert 90 <= results[0].numeric_value <= 110

    def test_overload(self):
        conn = _conn()
        _seed_daily_metrics(conn, "2026-04-01", ctl=30.0, atl=60.0)
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = RTTICalculator().compute(ctx)
        assert results[0].numeric_value > 150

    def test_no_data(self):
        conn = _conn()
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = RTTICalculator().compute(ctx)
        assert len(results) == 0

    def test_category(self):
        conn = _conn()
        _seed_daily_metrics(conn, "2026-04-01", ctl=50.0, atl=50.0)
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = RTTICalculator().compute(ctx)
        if results:
            assert results[0].category == "rp_load"
