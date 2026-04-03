import sqlite3
import json
import pytest
from src.db_setup import create_tables
from src.utils.db_helpers import upsert_metric
from src.metrics.base import CalcContext
from src.metrics.wlei import WLEICalculator

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


class TestWLEI:
    def test_basic(self):
        conn = _conn()
        aid = _seed_activity(conn)
        upsert_metric(conn, "activity", str(aid), "trimp",
                      "runpulse:formula_v1", numeric_value=100.0, category="rp_load")
        ctx = CalcContext(conn=conn, scope_type="activity", scope_id=str(aid))
        results = WLEICalculator().compute(ctx)
        assert len(results) == 1
        assert results[0].metric_name == "wlei"
        assert results[0].numeric_value >= 100

    def test_hot_weather(self):
        conn = _conn()
        aid = _seed_activity(conn, avg_temperature=35)
        upsert_metric(conn, "activity", str(aid), "trimp",
                      "runpulse:formula_v1", numeric_value=100.0, category="rp_load")
        ctx = CalcContext(conn=conn, scope_type="activity", scope_id=str(aid))
        results = WLEICalculator().compute(ctx)
        assert results[0].numeric_value > 100

    def test_cold_weather(self):
        conn = _conn()
        aid = _seed_activity(conn, avg_temperature=-5)
        upsert_metric(conn, "activity", str(aid), "trimp",
                      "runpulse:formula_v1", numeric_value=100.0, category="rp_load")
        ctx = CalcContext(conn=conn, scope_type="activity", scope_id=str(aid))
        results = WLEICalculator().compute(ctx)
        assert results[0].numeric_value > 100

    def test_no_trimp(self):
        conn = _conn()
        aid = _seed_activity(conn)
        ctx = CalcContext(conn=conn, scope_type="activity", scope_id=str(aid))
        results = WLEICalculator().compute(ctx)
        assert len(results) == 0

    def test_json_value(self):
        conn = _conn()
        aid = _seed_activity(conn)
        upsert_metric(conn, "activity", str(aid), "trimp",
                      "runpulse:formula_v1", numeric_value=80.0, category="rp_load")
        ctx = CalcContext(conn=conn, scope_type="activity", scope_id=str(aid))
        results = WLEICalculator().compute(ctx)
        jv = results[0].json_value
        assert "trimp" in jv
        assert "temp_c" in jv

    def test_confidence(self):
        conn = _conn()
        aid = _seed_activity(conn)
        upsert_metric(conn, "activity", str(aid), "trimp",
                      "runpulse:formula_v1", numeric_value=100.0, category="rp_load")
        ctx = CalcContext(conn=conn, scope_type="activity", scope_id=str(aid))
        results = WLEICalculator().compute(ctx)
        assert results[0].confidence is not None
        assert 0 < results[0].confidence <= 1.0
