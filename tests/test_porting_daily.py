import json
"""v0.2→v0.3 포팅 daily-scope 메트릭 테스트:
teroi, tpdi, rec, rtti, critical_power, sapi, rri, eftp, vdot_adj, marathon_shape, crs
"""
import sqlite3
import pytest

from src.db_setup import create_tables
from src.utils.db_helpers import upsert_metric
from src.metrics.base import CalcContext


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
        "avg_hr": 155, "max_hr": 185, "avg_pace_sec_km": 300,
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
    """helper: upsert multiple daily metrics"""
    for name, val in metrics.items():
        upsert_metric(conn, "daily", d, name, "runpulse:formula_v1",
                      numeric_value=val, category="rp_load")


def _seed_trimp_history(conn, base_date="2026-04-01", days=50):
    from datetime import datetime, timedelta
    target = datetime.strptime(base_date, "%Y-%m-%d")
    for i in range(days):
        d = target - timedelta(days=i)
        ds = d.strftime("%Y-%m-%d")
        aid = _seed_activity(conn, ds, source_id=f"a{i}")
        trimp_val = 80.0 + (i % 7) * 10
        upsert_metric(conn, "activity", str(aid), "trimp",
                      "runpulse:formula_v1", numeric_value=trimp_val, category="rp_load")


# ══════════════════════════════════════════
# TEROI
# ══════════════════════════════════════════
class TestTEROI:
    def test_with_data(self):
        from src.metrics.teroi import TEROICalculator
        conn = _conn()
        _seed_trimp_history(conn, days=30)
        _seed_daily_metrics(conn, "2026-04-01", ctl=45.0)
        _seed_daily_metrics(conn, "2026-03-04", ctl=30.0)
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = TEROICalculator().compute(ctx)
        assert len(results) == 1
        assert results[0].metric_name == "teroi"

    def test_no_trimp(self):
        from src.metrics.teroi import TEROICalculator
        conn = _conn()
        _seed_daily_metrics(conn, "2026-04-01", ctl=45.0)
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = TEROICalculator().compute(ctx)
        assert len(results) == 0


# ══════════════════════════════════════════
# REC
# ══════════════════════════════════════════
class TestREC:
    def test_with_data(self):
        from src.metrics.rec import RECCalculator
        conn = _conn()
        for i in range(5):
            d = f"2026-03-{28+i:02d}"
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
        from src.metrics.rec import RECCalculator
        conn = _conn()
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = RECCalculator().compute(ctx)
        assert len(results) == 0


# ══════════════════════════════════════════
# RTTI
# ══════════════════════════════════════════
class TestRTTI:
    def test_optimal(self):
        from src.metrics.rtti import RTTICalculator
        conn = _conn()
        _seed_wellness(conn, "2026-04-01", body_battery_high=80, sleep_score=85)
        _seed_daily_metrics(conn, "2026-04-01", ctl=50.0, atl=50.0)
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = RTTICalculator().compute(ctx)
        assert len(results) == 1
        assert 90 <= results[0].numeric_value <= 110  # ~100 적정

    def test_overload(self):
        from src.metrics.rtti import RTTICalculator
        conn = _conn()
        _seed_daily_metrics(conn, "2026-04-01", ctl=30.0, atl=60.0)
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = RTTICalculator().compute(ctx)
        assert results[0].numeric_value > 150

    def test_no_data(self):
        from src.metrics.rtti import RTTICalculator
        conn = _conn()
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = RTTICalculator().compute(ctx)
        assert len(results) == 0


# ══════════════════════════════════════════
# CriticalPower
# ══════════════════════════════════════════
class TestCriticalPower:
    def test_with_power_data(self):
        from src.metrics.critical_power import CriticalPowerCalculator
        conn = _conn()
        # 파워 데이터가 있는 활동 5개 시드
        for i, (pwr, dur) in enumerate([
            (300, 180), (280, 300), (260, 600), (240, 1200), (220, 2400)
        ]):
            _seed_activity(conn, f"2026-03-{20+i:02d}",
                           source_id=f"cp{i}", avg_power=pwr,
                           moving_time_sec=dur)
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = CriticalPowerCalculator().compute(ctx)
        assert len(results) == 1
        assert results[0].numeric_value > 0

    def test_no_power(self):
        from src.metrics.critical_power import CriticalPowerCalculator
        conn = _conn()
        _seed_activity(conn)  # avg_power 없음
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = CriticalPowerCalculator().compute(ctx)
        assert len(results) == 0


# ══════════════════════════════════════════
# RRI
# ══════════════════════════════════════════
class TestRRI:
    def test_with_all_inputs(self):
        from src.metrics.rri import RRICalculator
        conn = _conn()
        _seed_daily_metrics(conn, "2026-04-01",
                            runpulse_vdot=50.0, ctl=45.0, di=75.0, cirs=25.0)
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = RRICalculator().compute(ctx)
        assert len(results) == 1
        assert 0 <= results[0].numeric_value <= 100

    def test_high_cirs_lowers_rri(self):
        from src.metrics.rri import RRICalculator
        conn = _conn()
        _seed_daily_metrics(conn, "2026-04-01",
                            runpulse_vdot=50.0, ctl=45.0, di=75.0, cirs=80.0)
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = RRICalculator().compute(ctx)
        assert results[0].numeric_value < 50  # CIRS 높으면 RRI 낮음

    def test_no_vdot(self):
        from src.metrics.rri import RRICalculator
        conn = _conn()
        _seed_daily_metrics(conn, "2026-04-01", ctl=45.0)
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = RRICalculator().compute(ctx)
        assert len(results) == 0


# ══════════════════════════════════════════
# EFTP
# ══════════════════════════════════════════
class TestEFTP:
    def test_from_vdot(self):
        from src.metrics.eftp import EFTPCalculator
        conn = _conn()
        _seed_daily_metrics(conn, "2026-04-01", runpulse_vdot=50.0)
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = EFTPCalculator().compute(ctx)
        assert len(results) == 1
        assert results[0].metric_name == "eftp"
        assert 200 < results[0].numeric_value < 300  # VDOT 50 → T-pace ~239

    def test_no_vdot(self):
        from src.metrics.eftp import EFTPCalculator
        conn = _conn()
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = EFTPCalculator().compute(ctx)
        assert len(results) == 0


# ══════════════════════════════════════════
# VDOTAdj
# ══════════════════════════════════════════
class TestVDOTAdj:
    def test_passthrough(self):
        """역치런 데이터 없으면 기본 VDOT 반환"""
        from src.metrics.vdot_adj import VDOTAdjCalculator
        conn = _conn()
        _seed_daily_metrics(conn, "2026-04-01", runpulse_vdot=50.0)
        _seed_wellness(conn, "2026-04-01")
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = VDOTAdjCalculator().compute(ctx)
        assert len(results) == 1
        assert abs(results[0].numeric_value - 50.0) < 5.0

    def test_no_vdot(self):
        from src.metrics.vdot_adj import VDOTAdjCalculator
        conn = _conn()
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = VDOTAdjCalculator().compute(ctx)
        assert len(results) == 0


# ══════════════════════════════════════════
# MarathonShape
# ══════════════════════════════════════════
class TestMarathonShape:
    def test_with_data(self):
        from src.metrics.marathon_shape import MarathonShapeCalculator
        conn = _conn()
        _seed_daily_metrics(conn, "2026-04-01", runpulse_vdot=50.0)
        # 4주간 주 60km 러닝
        from datetime import datetime, timedelta
        for i in range(28):
            d = (datetime(2026, 4, 1) - timedelta(days=i)).strftime("%Y-%m-%d")
            _seed_activity(conn, d, source_id=f"ms{i}",
                           distance_m=8500, moving_time_sec=2800)
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = MarathonShapeCalculator().compute(ctx)
        assert len(results) == 1
        assert 0 < results[0].numeric_value <= 100
        assert (json.loads(results[0].json_value) if isinstance(results[0].json_value, str) else results[0].json_value)["label"] in [
            "insufficient", "base", "building", "ready", "peak"
        ]

    def test_no_vdot(self):
        from src.metrics.marathon_shape import MarathonShapeCalculator
        conn = _conn()
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = MarathonShapeCalculator().compute(ctx)
        assert len(results) == 0


# ══════════════════════════════════════════
# CRS
# ══════════════════════════════════════════
class TestCRS:
    def test_full_level(self):
        """모든 신호 정상 → level FULL"""
        from src.metrics.crs import CRSCalculator
        conn = _conn()
        _seed_wellness(conn, "2026-04-01", body_battery_high=80, hrv_weekly_avg=55)
        _seed_daily_metrics(conn, "2026-04-01",
                            acwr=1.1, tsb=5.0, cirs=20.0, utrs=75.0)
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = CRSCalculator().compute(ctx)
        assert len(results) == 1
        jv = json.loads(results[0].json_value) if isinstance(results[0].json_value, str) else results[0].json_value
        assert jv["level"] >= 3  # FULL or BOOST

    def test_high_acwr_restricts(self):
        """ACWR > 1.5 → level Z1"""
        from src.metrics.crs import CRSCalculator
        conn = _conn()
        _seed_wellness(conn, "2026-04-01")
        _seed_daily_metrics(conn, "2026-04-01",
                            acwr=1.8, tsb=-10.0, cirs=30.0, utrs=60.0)
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = CRSCalculator().compute(ctx)
        jv = json.loads(results[0].json_value) if isinstance(results[0].json_value, str) else results[0].json_value
        assert jv["level"] <= 1

    def test_low_body_battery(self):
        """BB < 20 → REST"""
        from src.metrics.crs import CRSCalculator
        conn = _conn()
        _seed_wellness(conn, "2026-04-01", body_battery_high=15)
        _seed_daily_metrics(conn, "2026-04-01",
                            acwr=1.0, tsb=0.0, cirs=20.0, utrs=60.0)
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = CRSCalculator().compute(ctx)
        jv = json.loads(results[0].json_value) if isinstance(results[0].json_value, str) else results[0].json_value
        assert jv["level"] == 0  # REST

    def test_boost_condition(self):
        """FULL + CRS>=80 + TSB>5 → BOOST"""
        from src.metrics.crs import CRSCalculator
        conn = _conn()
        _seed_wellness(conn, "2026-04-01", body_battery_high=90, hrv_weekly_avg=60)
        _seed_daily_metrics(conn, "2026-04-01",
                            acwr=1.1, tsb=10.0, cirs=10.0, utrs=85.0)
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = CRSCalculator().compute(ctx)
        jv = json.loads(results[0].json_value) if isinstance(results[0].json_value, str) else results[0].json_value
        assert jv["level"] == 4  # BOOST
        assert jv["boost_allowed"] is True

    def test_no_signals(self):
        """신호 없어도 결과 반환 (게이트 통과)"""
        from src.metrics.crs import CRSCalculator
        conn = _conn()
        _seed_wellness(conn, "2026-04-01")
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = CRSCalculator().compute(ctx)
        assert len(results) == 1
        assert (json.loads(results[0].json_value) if isinstance(results[0].json_value, str) else results[0].json_value)["level"] >= 3  # 데이터 없으면 FULL 통과


# ══════════════════════════════════════════
# TPDI — 실내/실외 데이터 모두 필요해서 빈 결과 테스트만
# ══════════════════════════════════════════
class TestTPDI:
    def test_no_indoor(self):
        from src.metrics.tpdi import TPDICalculator
        conn = _conn()
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = TPDICalculator().compute(ctx)
        assert len(results) == 0


# ══════════════════════════════════════════
# SAPI — 최소 데이터 부족 시 빈 결과
# ══════════════════════════════════════════
class TestSAPI:
    def test_no_fearp(self):
        from src.metrics.sapi import SAPICalculator
        conn = _conn()
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = SAPICalculator().compute(ctx)
        assert len(results) == 0
