import sqlite3
import json
import pytest
from src.db_setup import create_tables
from src.utils.db_helpers import upsert_metric
from src.metrics.base import CalcContext
from src.metrics.rec import RECCalculator

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


class TestREC:
    def test_with_data(self):
        conn = _conn()
        for i in range(5):
            d = f"2026-03-{28+i:02d}" if 28+i <= 31 else f"2026-04-{28+i-31:02d}"
            aid = _seed_activity(conn, d, source_id=f"r{i}")
            upsert_metric(conn, "activity", str(aid), "efficiency_factor_rp",
                          "runpulse:formula_v1", numeric_value=1.5, category="rp_performance")
            upsert_metric(conn, "activity", str(aid), "aerobic_decoupling_rp",
                          "runpulse:formula_v1", numeric_value=4.0, category="rp_performance")
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = RECCalculator().compute(ctx)
        assert len(results) == 1
        assert 0 <= results[0].numeric_value <= 100

    def test_no_ef(self):
        conn = _conn()
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = RECCalculator().compute(ctx)
        assert len(results) == 0

    def test_category(self):
        conn = _conn()
        for i in range(5):
            d = f"2026-03-{28+i:02d}" if 28+i <= 31 else f"2026-04-{28+i-31:02d}"
            aid = _seed_activity(conn, d, source_id=f"rc{i}")
            upsert_metric(conn, "activity", str(aid), "efficiency_factor_rp",
                          "runpulse:formula_v1", numeric_value=1.5, category="rp_performance")
            upsert_metric(conn, "activity", str(aid), "aerobic_decoupling_rp",
                          "runpulse:formula_v1", numeric_value=4.0, category="rp_performance")
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = RECCalculator().compute(ctx)
        assert results[0].category == "rp_efficiency"
