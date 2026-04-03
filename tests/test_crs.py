import sqlite3
import json
import pytest
from src.db_setup import create_tables
from src.utils.db_helpers import upsert_metric
from src.metrics.base import CalcContext
from src.metrics.crs import CRSCalculator

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


class TestCRS:
    def test_full_level(self):
        conn = _conn()
        _seed_wellness(conn, "2026-04-01", body_battery_high=80, hrv_weekly_avg=55)
        _seed_daily_metrics(conn, "2026-04-01",
                            acwr=1.1, tsb=5.0, cirs=20.0, utrs=75.0)
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = CRSCalculator().compute(ctx)
        assert len(results) == 1
        jv = json.loads(results[0].json_value) if isinstance(results[0].json_value, str) else results[0].json_value
        assert jv["level"] >= 3

    def test_high_acwr_restricts(self):
        conn = _conn()
        _seed_wellness(conn, "2026-04-01")
        _seed_daily_metrics(conn, "2026-04-01",
                            acwr=1.8, tsb=-10.0, cirs=30.0, utrs=60.0)
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = CRSCalculator().compute(ctx)
        jv = json.loads(results[0].json_value) if isinstance(results[0].json_value, str) else results[0].json_value
        assert jv["level"] <= 1

    def test_low_body_battery(self):
        conn = _conn()
        _seed_wellness(conn, "2026-04-01", body_battery_high=15)
        _seed_daily_metrics(conn, "2026-04-01",
                            acwr=1.0, tsb=0.0, cirs=20.0, utrs=60.0)
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = CRSCalculator().compute(ctx)
        jv = json.loads(results[0].json_value) if isinstance(results[0].json_value, str) else results[0].json_value
        assert jv["level"] == 0

    def test_boost_condition(self):
        conn = _conn()
        _seed_wellness(conn, "2026-04-01", body_battery_high=90, hrv_weekly_avg=60)
        _seed_daily_metrics(conn, "2026-04-01",
                            acwr=1.1, tsb=10.0, cirs=10.0, utrs=85.0)
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = CRSCalculator().compute(ctx)
        jv = json.loads(results[0].json_value) if isinstance(results[0].json_value, str) else results[0].json_value
        assert jv["level"] == 4
        assert jv["boost_allowed"] is True

    def test_no_signals(self):
        conn = _conn()
        _seed_wellness(conn, "2026-04-01")
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = CRSCalculator().compute(ctx)
        assert len(results) == 1
        jv = json.loads(results[0].json_value) if isinstance(results[0].json_value, str) else results[0].json_value
        assert jv["level"] >= 3

    def test_category(self):
        conn = _conn()
        _seed_wellness(conn, "2026-04-01")
        _seed_daily_metrics(conn, "2026-04-01", acwr=1.1, utrs=70.0)
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = CRSCalculator().compute(ctx)
        assert results[0].category == "rp_readiness"
