import sqlite3
import json
import pytest
from src.db_setup import create_tables
from src.utils.db_helpers import upsert_metric
from src.metrics.base import CalcContext
from src.metrics.tpdi import TPDICalculator

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


class TestTPDI:
    def test_with_indoor_outdoor(self):
        conn = _conn()
        for i in range(3):
            conn.execute(
                "INSERT INTO activity_summaries "
                "(source, source_id, name, activity_type, start_time, "
                "distance_m, moving_time_sec) VALUES (?,?,?,?,?,?,?)",
                ["garmin", f"out{i}", "Run", "running",
                 f"2026-03-{20+i:02d} 08:00:00", 10000, 3000])
            aid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            upsert_metric(conn, "activity", str(aid), "fearp",
                          "runpulse:formula_v1", numeric_value=300.0 + i*5,
                          category="rp_performance")
        for i in range(3):
            conn.execute(
                "INSERT INTO activity_summaries "
                "(source, source_id, name, activity_type, start_time, "
                "distance_m, moving_time_sec) VALUES (?,?,?,?,?,?,?)",
                ["garmin", f"in{i}", "Treadmill", "treadmill",
                 f"2026-03-{23+i:02d} 08:00:00", 8000, 2800])
            aid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            upsert_metric(conn, "activity", str(aid), "fearp",
                          "runpulse:formula_v1", numeric_value=280.0 + i*5,
                          category="rp_performance")
        conn.commit()
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = TPDICalculator().compute(ctx)
        assert len(results) == 1
        assert results[0].metric_name == "tpdi"
        assert isinstance(results[0].numeric_value, float)

    def test_json_has_counts(self):
        conn = _conn()
        for i in range(2):
            conn.execute(
                "INSERT INTO activity_summaries "
                "(source, source_id, name, activity_type, start_time, "
                "distance_m, moving_time_sec) VALUES (?,?,?,?,?,?,?)",
                ["garmin", f"o{i}", "Run", "running",
                 f"2026-03-{20+i:02d} 08:00:00", 10000, 3000])
            aid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            upsert_metric(conn, "activity", str(aid), "fearp",
                          "runpulse:formula_v1", numeric_value=310.0,
                          category="rp_performance")
        for i in range(2):
            conn.execute(
                "INSERT INTO activity_summaries "
                "(source, source_id, name, activity_type, start_time, "
                "distance_m, moving_time_sec) VALUES (?,?,?,?,?,?,?)",
                ["garmin", f"t{i}", "Treadmill", "treadmill",
                 f"2026-03-{22+i:02d} 08:00:00", 8000, 2800])
            aid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            upsert_metric(conn, "activity", str(aid), "fearp",
                          "runpulse:formula_v1", numeric_value=290.0,
                          category="rp_performance")
        conn.commit()
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = TPDICalculator().compute(ctx)
        assert len(results) == 1
        jv = json.loads(results[0].json_value) if isinstance(results[0].json_value, str) else results[0].json_value
        assert "outdoor_count" in jv and jv["outdoor_count"] >= 2
        assert "indoor_count" in jv and jv["indoor_count"] >= 2

    def test_no_indoor(self):
        conn = _conn()
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = TPDICalculator().compute(ctx)
        assert len(results) == 0
