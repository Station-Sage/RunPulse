"""v0.2→v0.3 포팅 activity-scope 메트릭 테스트: relative_effort, wlei"""
import sqlite3
import pytest

from src.db_setup import create_tables
from src.utils.db_helpers import upsert_metric
from src.metrics.base import CalcContext
from src.metrics.relative_effort import RelativeEffortCalculator
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


# ══════════════════════════════════════════
# RelativeEffort
# ══════════════════════════════════════════
class TestRelativeEffort:
    def test_from_avg_hr(self):
        """avg_hr/max_hr 기반 근사 계산"""
        conn = _conn()
        aid = _seed_activity(conn, avg_hr=155, max_hr=185)
        ctx = CalcContext(conn=conn, scope_type="activity", scope_id=str(aid))
        results = RelativeEffortCalculator().compute(ctx)
        assert len(results) == 1
        assert results[0].metric_name == "relative_effort"
        assert results[0].numeric_value > 0

    def test_high_intensity(self):
        """고강도(avg_hr/max_hr > 0.9) → 높은 RE"""
        conn = _conn()
        aid = _seed_activity(conn, avg_hr=175, max_hr=185, moving_time_sec=3600)
        ctx = CalcContext(conn=conn, scope_type="activity", scope_id=str(aid))
        results = RelativeEffortCalculator().compute(ctx)
        assert results[0].numeric_value > 100

    def test_low_intensity(self):
        """저강도 → 낮은 RE"""
        conn = _conn()
        aid = _seed_activity(conn, avg_hr=100, max_hr=185, moving_time_sec=3600)
        ctx = CalcContext(conn=conn, scope_type="activity", scope_id=str(aid))
        results = RelativeEffortCalculator().compute(ctx)
        assert results[0].numeric_value < 100

    def test_no_hr(self):
        """HR 없으면 빈 결과"""
        conn = _conn()
        aid = _seed_activity(conn, avg_hr=None, max_hr=None)
        ctx = CalcContext(conn=conn, scope_type="activity", scope_id=str(aid))
        results = RelativeEffortCalculator().compute(ctx)
        assert len(results) == 0

    def test_confidence_from_avg_hr(self):
        """단일 zone 근사 → confidence 0.6"""
        conn = _conn()
        aid = _seed_activity(conn)
        ctx = CalcContext(conn=conn, scope_type="activity", scope_id=str(aid))
        results = RelativeEffortCalculator().compute(ctx)
        assert results[0].confidence == 0.6


# ══════════════════════════════════════════
# WLEI
# ══════════════════════════════════════════
class TestWLEI:
    def test_basic(self):
        """TRIMP 있으면 WLEI 계산"""
        conn = _conn()
        aid = _seed_activity(conn)
        upsert_metric(conn, "activity", str(aid), "trimp",
                      "runpulse:formula_v1", numeric_value=100.0, category="rp_load")
        ctx = CalcContext(conn=conn, scope_type="activity", scope_id=str(aid))
        results = WLEICalculator().compute(ctx)
        assert len(results) == 1
        assert results[0].metric_name == "wlei"
        assert results[0].numeric_value >= 100  # 기본 날씨(20°C, 60%) → stress=1.0

    def test_hot_weather(self):
        """더운 날씨 → WLEI > TRIMP"""
        conn = _conn()
        aid = _seed_activity(conn, avg_temperature=35)
        upsert_metric(conn, "activity", str(aid), "trimp",
                      "runpulse:formula_v1", numeric_value=100.0, category="rp_load")
        ctx = CalcContext(conn=conn, scope_type="activity", scope_id=str(aid))
        results = WLEICalculator().compute(ctx)
        assert results[0].numeric_value > 100

    def test_cold_weather(self):
        """추운 날씨 → WLEI > TRIMP"""
        conn = _conn()
        aid = _seed_activity(conn, avg_temperature=-5)
        upsert_metric(conn, "activity", str(aid), "trimp",
                      "runpulse:formula_v1", numeric_value=100.0, category="rp_load")
        ctx = CalcContext(conn=conn, scope_type="activity", scope_id=str(aid))
        results = WLEICalculator().compute(ctx)
        assert results[0].numeric_value > 100

    def test_no_trimp(self):
        """TRIMP 없으면 빈 결과"""
        conn = _conn()
        aid = _seed_activity(conn)
        ctx = CalcContext(conn=conn, scope_type="activity", scope_id=str(aid))
        results = WLEICalculator().compute(ctx)
        assert len(results) == 0

    def test_json_value(self):
        """json_value에 temp/humidity 포함"""
        conn = _conn()
        aid = _seed_activity(conn)
        upsert_metric(conn, "activity", str(aid), "trimp",
                      "runpulse:formula_v1", numeric_value=80.0, category="rp_load")
        ctx = CalcContext(conn=conn, scope_type="activity", scope_id=str(aid))
        results = WLEICalculator().compute(ctx)
        jv = results[0].json_value
        assert "trimp" in jv
        assert "temp_c" in jv
        assert "humidity_pct" in jv
