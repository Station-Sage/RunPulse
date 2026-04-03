"""PMC (Performance Management Chart) 단위 테스트 — 설계서 4-6."""
import sqlite3, pytest
from datetime import datetime, timedelta
from src.db_setup import create_tables
from src.metrics.base import CalcContext
from src.metrics.pmc import PMCCalculator
from src.utils.db_helpers import upsert_metric


def _conn():
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys=ON")
    create_tables(conn)
    return conn


def _seed_trimp(conn, base="2026-04-01", days=50, trimp_fn=None):
    target = datetime.strptime(base, "%Y-%m-%d")
    for i in range(days):
        d = (target - timedelta(days=i)).strftime("%Y-%m-%d")
        conn.execute(
            "INSERT INTO activity_summaries "
            "(source, source_id, name, activity_type, start_time, "
            "distance_m, moving_time_sec, avg_hr, max_hr) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            ["garmin", f"a{i}", "Run", "running",
             f"{d} 08:00:00", 10000, 3000, 155, 185])
        aid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        val = trimp_fn(i) if trimp_fn else 80.0 + (i % 7) * 10
        upsert_metric(conn, "activity", str(aid), "trimp",
                       "runpulse:formula_v1", numeric_value=val, category="rp_load")
    conn.commit()


class TestPMC:
    def test_produces_four_metrics(self):
        conn = _conn()
        _seed_trimp(conn)
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = PMCCalculator().compute(ctx)
        names = {r.metric_name for r in results}
        assert {"ctl", "atl", "tsb", "ramp_rate"} == names
        for r in results:
            assert r.numeric_value is not None

    def test_ctl_increases_with_training(self):
        """설계서 4-6: 매일 훈련하면 CTL이 증가."""
        conn = _conn()
        _seed_trimp(conn, days=50)
        early = PMCCalculator().compute(
            CalcContext(conn=conn, scope_type="daily", scope_id="2026-03-15"))
        late = PMCCalculator().compute(
            CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01"))
        ctl_early = next((r.numeric_value for r in early if r.metric_name == "ctl"), 0)
        ctl_late = next((r.numeric_value for r in late if r.metric_name == "ctl"), 0)
        assert ctl_late > ctl_early

    def test_tsb_negative_after_hard_training(self):
        """설계서 4-6: 고강도 훈련 직후 TSB < 0."""
        conn = _conn()
        # 최근 7일 고강도, 이전 35일 저강도
        _seed_trimp(conn, days=42,
                    trimp_fn=lambda i: 200.0 if i < 7 else 30.0)
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = PMCCalculator().compute(ctx)
        tsb = next((r.numeric_value for r in results if r.metric_name == "tsb"), None)
        assert tsb is not None and tsb < 0

    def test_no_data(self):
        conn = _conn()
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        assert PMCCalculator().compute(ctx) == []
