"""CIRS (Composite Injury Risk Score) 단위 테스트 — 설계서 4-6."""
import sqlite3, pytest
from src.db_setup import create_tables
from src.metrics.base import CalcContext
from src.metrics.cirs import CIRSCalculator
from src.utils.db_helpers import upsert_metric


def _conn():
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys=ON")
    create_tables(conn)
    return conn


def _seed_load_metrics(conn, acwr=1.0, monotony=1.5, lsi=1.0):
    upsert_metric(conn, "daily", "2026-04-01", "acwr",
                   "runpulse:formula_v1", numeric_value=acwr, category="rp_load")
    upsert_metric(conn, "daily", "2026-04-01", "monotony",
                   "runpulse:formula_v1", numeric_value=monotony, category="rp_load")
    upsert_metric(conn, "daily", "2026-04-01", "lsi",
                   "runpulse:formula_v1", numeric_value=lsi, category="rp_load")
    conn.commit()


class TestCIRS:
    def test_high_acwr_means_high_cirs(self):
        """설계서 4-6: ACWR > 1.5 → CIRS 높음."""
        conn = _conn()
        _seed_load_metrics(conn, acwr=1.8, monotony=2.5, lsi=2.0)
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = CIRSCalculator().compute(ctx)
        assert len(results) == 1
        assert results[0].numeric_value >= 50

    def test_optimal_acwr_means_low_cirs(self):
        """설계서 4-6: ACWR 0.8~1.3 → CIRS 낮음."""
        conn = _conn()
        _seed_load_metrics(conn, acwr=1.0, monotony=1.2, lsi=0.8)
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = CIRSCalculator().compute(ctx)
        assert len(results) == 1
        assert results[0].numeric_value < 30

    def test_confidence_present(self):
        """confidence 필드 설정 확인."""
        conn = _conn()
        _seed_load_metrics(conn, acwr=1.4, monotony=1.8, lsi=1.5)
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = CIRSCalculator().compute(ctx)
        assert results[0].confidence is not None
        assert 0 < results[0].confidence <= 1.0

    def test_category_is_rp_risk(self):
        conn = _conn()
        _seed_load_metrics(conn, acwr=1.4, monotony=1.8, lsi=1.5)
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = CIRSCalculator().compute(ctx)
        assert results[0].category == "rp_risk"

    def test_no_data(self):
        conn = _conn()
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        assert CIRSCalculator().compute(ctx) == []
