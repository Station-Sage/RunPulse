"""Daily-Scope 2차 calculator 테스트."""
import sqlite3, pytest
from src.db_setup import create_tables
from src.metrics.base import CalcContext
from src.utils.db_helpers import upsert_metric
from src.metrics.utrs import UTRSCalculator
from src.metrics.cirs import CIRSCalculator
from src.metrics.fearp import FEARPCalculator
from src.metrics.rmr import RMRCalculator
from src.metrics.adti import ADTICalculator


def _conn():
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys=ON")
    create_tables(conn)
    return conn


class TestUTRS:
    def test_with_wellness_and_tsb(self):
        conn = _conn()
        conn.execute(
            "INSERT INTO daily_wellness (date, body_battery_high, sleep_score, resting_hr) "
            "VALUES (?, ?, ?, ?)", ["2026-04-01", 80, 85, 52])
        upsert_metric(conn, "daily", "2026-04-01", "tsb",
                       "runpulse:formula_v1", numeric_value=5.0, category="rp_load")
        conn.commit()
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = UTRSCalculator().compute(ctx)
        assert len(results) == 1
        assert 0 <= results[0].numeric_value <= 100
        assert results[0].confidence > 0

    def test_no_data(self):
        conn = _conn()
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        assert UTRSCalculator().compute(ctx) == []


class TestCIRS:
    def test_with_metrics(self):
        conn = _conn()
        upsert_metric(conn, "daily", "2026-04-01", "acwr",
                       "runpulse:formula_v1", numeric_value=1.4, category="rp_load")
        upsert_metric(conn, "daily", "2026-04-01", "monotony",
                       "runpulse:formula_v1", numeric_value=2.5, category="rp_load")
        upsert_metric(conn, "daily", "2026-04-01", "lsi",
                       "runpulse:formula_v1", numeric_value=1.8, category="rp_load")
        conn.commit()
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = CIRSCalculator().compute(ctx)
        assert len(results) == 1
        assert results[0].numeric_value > 0

    def test_no_data(self):
        conn = _conn()
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        assert CIRSCalculator().compute(ctx) == []


class TestFEARP:
    def test_compute(self):
        conn = _conn()
        conn.execute(
            "INSERT INTO activity_summaries "
            "(source, source_id, name, activity_type, start_time, "
            "distance_m, moving_time_sec, avg_hr, max_hr, avg_speed_ms, avg_temperature) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            ["garmin", "1", "Run", "running", "2026-04-01 08:00:00",
             10000, 3000, 155, 185, 3.33, 25.0])
        conn.commit()
        aid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        ctx = CalcContext(conn=conn, scope_type="activity", scope_id=str(aid))
        results = FEARPCalculator().compute(ctx)
        assert len(results) == 1
        assert results[0].numeric_value > 0

    def test_non_running(self):
        conn = _conn()
        conn.execute(
            "INSERT INTO activity_summaries "
            "(source, source_id, name, activity_type, start_time, distance_m, moving_time_sec) "
            "VALUES (?,?,?,?,?,?,?)",
            ["garmin", "1", "Ride", "cycling", "2026-04-01 08:00:00", 50000, 7200])
        conn.commit()
        aid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        ctx = CalcContext(conn=conn, scope_type="activity", scope_id=str(aid))
        assert FEARPCalculator().compute(ctx) == []


class TestRMR:
    def test_with_wellness(self):
        conn = _conn()
        conn.execute(
            "INSERT INTO daily_wellness (date, resting_hr, body_battery_high, sleep_score) "
            "VALUES (?, ?, ?, ?)", ["2026-04-01", 52, 85, 80])
        upsert_metric(conn, "daily", "2026-04-01", "tsb",
                       "runpulse:formula_v1", numeric_value=5.0, category="rp_load")
        conn.commit()
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = RMRCalculator().compute(ctx)
        assert len(results) == 1
        assert 0 <= results[0].numeric_value <= 100

    def test_no_data(self):
        conn = _conn()
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        assert RMRCalculator().compute(ctx) == []


class TestADTI:
    def test_with_ctl_series(self):
        conn = _conn()
        from datetime import datetime, timedelta
        target = datetime.strptime("2026-04-01", "%Y-%m-%d")
        for i in range(28):
            d = (target - timedelta(days=27-i)).strftime("%Y-%m-%d")
            ctl_val = 30.0 + i * 0.5  # 상승 추세
            upsert_metric(conn, "daily", d, "ctl",
                           "runpulse:formula_v1", numeric_value=ctl_val, category="rp_load")
        conn.commit()
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = ADTICalculator().compute(ctx)
        assert len(results) == 1
        assert results[0].numeric_value > 0  # 상승 추세

    def test_insufficient_data(self):
        conn = _conn()
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        assert ADTICalculator().compute(ctx) == []
