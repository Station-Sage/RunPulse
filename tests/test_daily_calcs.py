"""Daily-Scope 1차 calculator 테스트 (PMC, ACWR, LSI, Monotony)."""
import sqlite3, pytest
from src.db_setup import create_tables
from src.metrics.base import CalcContext
from src.utils.db_helpers import upsert_metric
from src.metrics.pmc import PMCCalculator
from src.metrics.acwr import ACWRCalculator
from src.metrics.lsi import LSICalculator
from src.metrics.monotony import MonotonyStrainCalculator


def _conn():
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys=ON")
    create_tables(conn)
    return conn


def _seed_trimp_history(conn, base_date="2026-04-01", days=50):
    """과거 N일간 활동 + TRIMP 생성."""
    from datetime import datetime, timedelta
    target = datetime.strptime(base_date, "%Y-%m-%d")
    for i in range(days):
        d = target - timedelta(days=i)
        date_str = d.strftime("%Y-%m-%d")
        # 활동 삽입
        conn.execute(
            "INSERT INTO activity_summaries "
            "(source, source_id, name, activity_type, start_time, "
            "distance_m, moving_time_sec, avg_hr, max_hr) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            ["garmin", f"a{i}", "Run", "running",
             f"{date_str} 08:00:00", 10000, 3000, 155, 185],
        )
        aid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        # TRIMP 저장 (50~150 범위)
        trimp_val = 80.0 + (i % 7) * 10
        upsert_metric(conn, "activity", str(aid), "trimp",
                       "runpulse:formula_v1", numeric_value=trimp_val,
                       category="rp_load")
    conn.commit()


class TestPMC:
    def test_compute(self):
        conn = _conn()
        _seed_trimp_history(conn, days=50)
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = PMCCalculator().compute(ctx)
        names = {r.metric_name for r in results}
        assert {"ctl", "atl", "tsb", "ramp_rate"} == names
        for r in results:
            assert r.numeric_value is not None

    def test_no_data(self):
        conn = _conn()
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        assert PMCCalculator().compute(ctx) == []


class TestACWR:
    def test_compute(self):
        conn = _conn()
        upsert_metric(conn, "daily", "2026-04-01", "atl",
                       "runpulse:formula_v1", numeric_value=80.0, category="rp_load")
        upsert_metric(conn, "daily", "2026-04-01", "ctl",
                       "runpulse:formula_v1", numeric_value=60.0, category="rp_load")
        conn.commit()
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = ACWRCalculator().compute(ctx)
        assert len(results) == 1
        assert abs(results[0].numeric_value - 1.33) < 0.01

    def test_no_ctl(self):
        conn = _conn()
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        assert ACWRCalculator().compute(ctx) == []


class TestLSI:
    def test_compute(self):
        conn = _conn()
        _seed_trimp_history(conn, days=30)
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = LSICalculator().compute(ctx)
        assert len(results) == 1
        assert results[0].numeric_value > 0

    def test_no_today(self):
        conn = _conn()
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2099-01-01")
        assert LSICalculator().compute(ctx) == []


class TestMonotony:
    def test_compute(self):
        conn = _conn()
        _seed_trimp_history(conn, days=10)
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = MonotonyStrainCalculator().compute(ctx)
        names = {r.metric_name for r in results}
        assert "monotony" in names

    def test_no_data(self):
        conn = _conn()
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2099-01-01")
        assert MonotonyStrainCalculator().compute(ctx) == []
