"""Activity-Scope calculator 테스트 (decoupling, gap, classifier, vdot, ef)."""
import sqlite3, json, pytest
from src.db_setup import create_tables
from src.metrics.base import CalcContext
from src.metrics.decoupling import AerobicDecouplingCalculator
from src.metrics.gap import GAPCalculator
from src.metrics.classifier import WorkoutClassifier
from src.metrics.vdot import VDOTCalculator
from src.metrics.efficiency import EfficiencyFactorCalculator


def _conn():
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys=ON")
    create_tables(conn)
    return conn


def _seed_activity(conn, **kw):
    d = {"source": "garmin", "source_id": "1", "name": "Run",
         "activity_type": "running", "start_time": "2026-04-01 08:00:00",
         "distance_m": 10000, "moving_time_sec": 3000,
         "avg_hr": 155, "max_hr": 185, "avg_speed_ms": 3.33}
    d.update(kw)
    cols = ", ".join(d.keys())
    vals = ", ".join("?" * len(d))
    conn.execute(f"INSERT INTO activity_summaries ({cols}) VALUES ({vals})", list(d.values()))
    conn.commit()
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def _seed_streams(conn, aid, n=200):
    for i in range(n):
        conn.execute(
            "INSERT INTO activity_streams "
            "(activity_id, source, elapsed_sec, speed_ms, heart_rate, grade_pct) "
            "VALUES (?,?,?,?,?,?)",
            [aid, "garmin", i, 3.3 + (0.01 * (i % 10)), 150 + (i % 20), (i % 5) - 2],
        )
    conn.commit()


class TestDecoupling:
    def test_with_streams(self):
        conn = _conn()
        aid = _seed_activity(conn, moving_time_sec=2400)
        _seed_streams(conn, aid, 300)
        ctx = CalcContext(conn=conn, scope_type="activity", scope_id=str(aid))
        results = AerobicDecouplingCalculator().compute(ctx)
        assert len(results) == 1
        assert results[0].metric_name == "aerobic_decoupling_rp"

    def test_too_short(self):
        conn = _conn()
        aid = _seed_activity(conn, moving_time_sec=600)
        ctx = CalcContext(conn=conn, scope_type="activity", scope_id=str(aid))
        assert AerobicDecouplingCalculator().compute(ctx) == []

    def test_no_streams(self):
        conn = _conn()
        aid = _seed_activity(conn, moving_time_sec=2400)
        ctx = CalcContext(conn=conn, scope_type="activity", scope_id=str(aid))
        assert AerobicDecouplingCalculator().compute(ctx) == []


class TestGAP:
    def test_with_streams(self):
        conn = _conn()
        aid = _seed_activity(conn)
        _seed_streams(conn, aid, 120)
        ctx = CalcContext(conn=conn, scope_type="activity", scope_id=str(aid))
        results = GAPCalculator().compute(ctx)
        assert len(results) == 1
        assert results[0].metric_name == "gap_rp"
        assert results[0].numeric_value > 0

    def test_no_streams(self):
        conn = _conn()
        aid = _seed_activity(conn)
        ctx = CalcContext(conn=conn, scope_type="activity", scope_id=str(aid))
        assert GAPCalculator().compute(ctx) == []


class TestClassifier:
    def test_easy_run(self):
        conn = _conn()
        aid = _seed_activity(conn, avg_hr=120, max_hr=185, distance_m=8000)
        ctx = CalcContext(conn=conn, scope_type="activity", scope_id=str(aid))
        results = WorkoutClassifier().compute(ctx)
        assert len(results) == 1
        data = json.loads(results[0].json_value)
        assert data["type"] in ("easy", "recovery")

    def test_long_run(self):
        conn = _conn()
        aid = _seed_activity(conn, distance_m=20000, moving_time_sec=7200, avg_hr=145)
        ctx = CalcContext(conn=conn, scope_type="activity", scope_id=str(aid))
        results = WorkoutClassifier().compute(ctx)
        data = json.loads(results[0].json_value)
        assert data["type"] == "long_run"

    def test_non_running(self):
        conn = _conn()
        aid = _seed_activity(conn, activity_type="cycling")
        ctx = CalcContext(conn=conn, scope_type="activity", scope_id=str(aid))
        assert WorkoutClassifier().compute(ctx) == []


class TestVDOT:
    def test_compute(self):
        conn = _conn()
        aid = _seed_activity(conn, distance_m=10000, moving_time_sec=2700)
        ctx = CalcContext(conn=conn, scope_type="activity", scope_id=str(aid))
        results = VDOTCalculator().compute(ctx)
        assert len(results) == 1
        assert results[0].metric_name == "runpulse_vdot"
        assert 30 < results[0].numeric_value < 80

    def test_too_short(self):
        conn = _conn()
        aid = _seed_activity(conn, distance_m=500, moving_time_sec=120)
        ctx = CalcContext(conn=conn, scope_type="activity", scope_id=str(aid))
        assert VDOTCalculator().compute(ctx) == []

    def test_non_running(self):
        conn = _conn()
        aid = _seed_activity(conn, activity_type="cycling")
        ctx = CalcContext(conn=conn, scope_type="activity", scope_id=str(aid))
        assert VDOTCalculator().compute(ctx) == []


class TestEF:
    def test_compute(self):
        conn = _conn()
        aid = _seed_activity(conn, avg_speed_ms=3.33, avg_hr=155)
        ctx = CalcContext(conn=conn, scope_type="activity", scope_id=str(aid))
        results = EfficiencyFactorCalculator().compute(ctx)
        assert len(results) == 1
        assert results[0].metric_name == "efficiency_factor_rp"
        assert results[0].numeric_value > 0

    def test_no_hr(self):
        conn = _conn()
        aid = _seed_activity(conn, avg_hr=None)
        ctx = CalcContext(conn=conn, scope_type="activity", scope_id=str(aid))
        assert EfficiencyFactorCalculator().compute(ctx) == []
