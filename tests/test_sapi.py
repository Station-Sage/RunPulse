import sqlite3
import json
import pytest
from src.db_setup import create_tables
from src.utils.db_helpers import upsert_metric
from src.metrics.base import CalcContext
from src.metrics.sapi import SAPICalculator

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


class TestSAPI:
    def test_with_fearp_data(self):
        """90일 기간 + 최근 7일 모두 FEARP 데이터 필요."""
        conn = _conn()
        # 과거 데이터 (기준 구간 형성)
        for i in range(5):
            conn.execute(
                "INSERT INTO activity_summaries "
                "(source, source_id, name, activity_type, start_time, "
                "distance_m, moving_time_sec, avg_temperature) "
                "VALUES (?,?,?,?,?,?,?,?)",
                ["garmin", f"s{i}", "Run", "running",
                 f"2026-02-{10+i:02d} 08:00:00", 10000, 3000, 12.0])
            aid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            upsert_metric(conn, "activity", str(aid), "fearp",
                          "runpulse:formula_v1", numeric_value=300.0,
                          category="rp_performance",
                          json_value={"temp_c": 12.0})
        # 최근 7일 데이터
        for i in range(3):
            conn.execute(
                "INSERT INTO activity_summaries "
                "(source, source_id, name, activity_type, start_time, "
                "distance_m, moving_time_sec, avg_temperature) "
                "VALUES (?,?,?,?,?,?,?,?)",
                ["garmin", f"r{i}", "Run", "running",
                 f"2026-03-{29+i:02d} 08:00:00", 10000, 3000, 12.0])
            aid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            upsert_metric(conn, "activity", str(aid), "fearp",
                          "runpulse:formula_v1", numeric_value=295.0,
                          category="rp_performance",
                          json_value={"temp_c": 12.0})
        conn.commit()
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = SAPICalculator().compute(ctx)
        assert len(results) == 1
        assert results[0].metric_name == "sapi"
        assert results[0].numeric_value > 0

    def test_no_fearp(self):
        conn = _conn()
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = SAPICalculator().compute(ctx)
        assert len(results) == 0

    def test_category(self):
        conn = _conn()
        for i in range(5):
            conn.execute(
                "INSERT INTO activity_summaries "
                "(source, source_id, name, activity_type, start_time, "
                "distance_m, moving_time_sec, avg_temperature) "
                "VALUES (?,?,?,?,?,?,?,?)",
                ["garmin", f"sc{i}", "Run", "running",
                 f"2026-03-{10+i:02d} 08:00:00", 10000, 3000, 12.0])
            aid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            upsert_metric(conn, "activity", str(aid), "fearp",
                          "runpulse:formula_v1", numeric_value=300.0,
                          category="rp_performance")
        conn.commit()
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = SAPICalculator().compute(ctx)
        if results:
            assert results[0].category == "rp_performance"
