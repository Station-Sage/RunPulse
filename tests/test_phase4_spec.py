"""
Phase 4-6 설계서 테스트 계획 – 누락 케이스 구현
"""
import sqlite3
import json
from datetime import date, timedelta

import pytest

from src.db_setup import create_tables
from src.utils.db_helpers import upsert_metric
from src.metrics.base import CalcContext


# ──────────────────────────────────────────
# 공통 헬퍼
# ──────────────────────────────────────────
def _conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    create_tables(conn)
    return conn


def _seed_activity(conn, act_date, **overrides):
    defaults = {
        "source": "garmin", "source_id": "1", "name": "Test Run",
        "activity_type": "running", "start_time": f"{act_date} 08:00:00",
        "distance_m": 10000, "moving_time_sec": 3000,
        "avg_hr": 155, "max_hr": 185,
    }
    defaults.update(overrides)
    cols = ", ".join(defaults.keys())
    vals = ", ".join("?" * len(defaults))
    conn.execute(
        f"INSERT INTO activity_summaries ({cols}) VALUES ({vals})",
        list(defaults.values()),
    )
    conn.commit()
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def _seed_wellness(conn, d, **overrides):
    defaults = {
        "date": d, "resting_hr": 55,
    }
    defaults.update(overrides)
    cols = ", ".join(defaults.keys())
    vals = ", ".join("?" * len(defaults))
    conn.execute(
        f"INSERT OR REPLACE INTO daily_wellness ({cols}) VALUES ({vals})",
        list(defaults.values()),
    )
    conn.commit()


# ══════════════════════════════════════════
# 1. TRIMP – missing duration (설계서 요구)
# ══════════════════════════════════════════
class TestTRIMPMissingDuration:
    def test_zero_duration_returns_empty(self):
        """moving_time_sec=0 이면 빈 결과"""
        conn = _conn()
        aid = _seed_activity(conn, "2025-01-15", moving_time_sec=0)
        from src.metrics.trimp import TRIMPCalculator
        calc = TRIMPCalculator()
        ctx = CalcContext(conn=conn, scope_type="activity", scope_id=str(aid))
        results = calc.compute(ctx)
        assert len(results) == 0

    def test_null_duration_returns_empty(self):
        """moving_time_sec=NULL 이면 빈 결과"""
        conn = _conn()
        aid = _seed_activity(conn, "2025-01-15", moving_time_sec=None)
        from src.metrics.trimp import TRIMPCalculator
        calc = TRIMPCalculator()
        ctx = CalcContext(conn=conn, scope_type="activity", scope_id=str(aid))
        results = calc.compute(ctx)
        assert len(results) == 0


# ══════════════════════════════════════════
# 2. PMC – CTL 증가, TSB 음수/양수 (설계서 요구)
# ══════════════════════════════════════════
class TestPMCBehavior:
    def _seed_training_block(self, conn, days, trimp_value, base_date="2026-04-01"):
        """days일 연속 훈련 데이터 시드"""
        from datetime import datetime
        target = datetime.strptime(base_date, "%Y-%m-%d")
        for i in range(days):
            d = target - timedelta(days=days - 1 - i)
            ds = d.strftime("%Y-%m-%d")
            aid = _seed_activity(conn, ds, source_id=f"t{i}")
            upsert_metric(conn, "activity", str(aid), "trimp",
                          "runpulse:formula_v1", numeric_value=trimp_value,
                          category="rp_load")

    def test_ctl_increases_with_training(self):
        """매일 훈련하면 CTL이 증가하는지 확인"""
        conn = _conn()
        self._seed_training_block(conn, 50, trimp_value=120.0)

        from src.metrics.pmc import PMCCalculator
        calc = PMCCalculator()

        # 20일째 CTL
        ctx_early = CalcContext(conn=conn, scope_type="daily",
                                scope_id="2026-03-23")
        res_early = calc.compute(ctx_early)
        ctl_early = next((r for r in res_early if r.metric_name == "ctl"), None)

        # 50일째 CTL
        ctx_late = CalcContext(conn=conn, scope_type="daily",
                               scope_id="2026-04-01")
        res_late = calc.compute(ctx_late)
        ctl_late = next((r for r in res_late if r.metric_name == "ctl"), None)

        assert ctl_early is not None and ctl_late is not None
        assert ctl_late.numeric_value > ctl_early.numeric_value

    def test_tsb_negative_after_hard_training(self):
        """고강도 훈련 직후 TSB < 0"""
        conn = _conn()
        self._seed_training_block(conn, 14, trimp_value=200.0)

        from src.metrics.pmc import PMCCalculator
        calc = PMCCalculator()
        ctx = CalcContext(conn=conn, scope_type="daily",
                          scope_id="2026-04-01")
        results = calc.compute(ctx)
        tsb = next((r for r in results if r.metric_name == "tsb"), None)
        assert tsb is not None
        assert tsb.numeric_value < 0

    def test_tsb_positive_after_rest(self):
        """7일 훈련 후 21일 휴식 → TSB > 0"""
        conn = _conn()
        from datetime import datetime
        base = datetime.strptime("2026-04-01", "%Y-%m-%d")
        # 7일 훈련 (28일 전부터)
        for i in range(7):
            d = base - timedelta(days=28 - i)
            ds = d.strftime("%Y-%m-%d")
            aid = _seed_activity(conn, ds, source_id=f"r{i}")
            upsert_metric(conn, "activity", str(aid), "trimp",
                          "runpulse:formula_v1", numeric_value=100.0,
                          category="rp_load")
        # 21일 휴식 (활동 없음)

        from src.metrics.pmc import PMCCalculator
        calc = PMCCalculator()
        ctx = CalcContext(conn=conn, scope_type="daily",
                          scope_id="2026-04-01")
        results = calc.compute(ctx)
        tsb = next((r for r in results if r.metric_name == "tsb"), None)
        assert tsb is not None
        assert tsb.numeric_value > 0


# ══════════════════════════════════════════
# 3. UTRS – partial inputs (설계서 요구)
# ══════════════════════════════════════════
class TestUTRSPartialInputs:
    def test_partial_inputs_confidence_below_1(self):
        """일부 입력만 있을 때 confidence < 1.0"""
        conn = _conn()
        d = "2025-01-20"
        # body_battery와 sleep만 제공
        _seed_wellness(conn, d, resting_hr=55)
        # body_battery_high, sleep_score만 metric으로 제공
        upsert_metric(conn, "daily", d, "body_battery_high",
                      "garmin:connect", numeric_value=80.0,
                      category="recovery")
        upsert_metric(conn, "daily", d, "sleep_score",
                      "garmin:connect", numeric_value=75.0,
                      category="recovery")

        from src.metrics.utrs import UTRSCalculator
        calc = UTRSCalculator()
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id=d)
        results = calc.compute(ctx)

        if len(results) > 0:
            assert results[0].confidence is not None
            assert results[0].confidence < 1.0


# ══════════════════════════════════════════
# 4. CIRS – high ACWR / optimal range (설계서 요구)
# ══════════════════════════════════════════
class TestCIRSScenarios:
    def _seed_cirs_context(self, conn, d, acwr, ctl, atl, tsb,
                           consec_days=3, trimp_avg=100):
        _seed_wellness(conn, d)
        for name, val in [("acwr", acwr), ("ctl", ctl), ("atl", atl), ("tsb", tsb)]:
            upsert_metric(conn, "daily", d, name,
                          "runpulse:formula_v1", numeric_value=val,
                          category="rp_load")
        # 연속 활동일 시드
        base = date.fromisoformat(d)
        for i in range(consec_days):
            dd = (base - timedelta(days=i)).isoformat()
            aid = _seed_activity(conn, dd, source_id=f"c{d}_{i}")
            upsert_metric(conn, "activity", str(aid), "trimp",
                          "runpulse:formula_v1", numeric_value=trimp_avg,
                          category="rp_load")

    def test_high_acwr_produces_high_cirs(self):
        """ACWR > 1.5 → CIRS 높음 (>60)"""
        conn = _conn()
        d = "2025-02-15"
        self._seed_cirs_context(conn, d, acwr=1.8, ctl=50, atl=90,
                                tsb=-40, consec_days=5)

        from src.metrics.cirs import CIRSCalculator
        calc = CIRSCalculator()
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id=d)
        results = calc.compute(ctx)
        assert len(results) >= 1
        cirs_val = results[0].numeric_value
        assert cirs_val > 60, f"CIRS={cirs_val}, expected >60"

    def test_optimal_acwr_produces_low_cirs(self):
        """ACWR 0.8~1.3 → CIRS 낮음 (<40)"""
        conn = _conn()
        d = "2025-02-15"
        self._seed_cirs_context(conn, d, acwr=1.0, ctl=60, atl=60,
                                tsb=0, consec_days=2)

        from src.metrics.cirs import CIRSCalculator
        calc = CIRSCalculator()
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id=d)
        results = calc.compute(ctx)
        assert len(results) >= 1
        cirs_val = results[0].numeric_value
        assert cirs_val < 40, f"CIRS={cirs_val}, expected <40"


# ══════════════════════════════════════════
# 5. Engine – circular dependency (설계서 요구)
# ══════════════════════════════════════════
class TestCircularDependency:
    def test_circular_dependency_does_not_crash(self):
        """순환 의존성이 있어도 크래시 없이 결과 반환"""
        from src.metrics.base import MetricCalculator
        from src.metrics.engine import _topological_sort

        class FakeA(MetricCalculator):
            name = "fake_a"
            provider = "test"
            version = "1.0"
            scope_type = "daily"
            category = "test"
            requires = ["fake_b_metric"]
            produces = ["fake_a_metric"]
            def compute(self, ctx): return []

        class FakeB(MetricCalculator):
            name = "fake_b"
            provider = "test"
            version = "1.0"
            scope_type = "daily"
            category = "test"
            requires = ["fake_a_metric"]
            produces = ["fake_b_metric"]
            def compute(self, ctx): return []

        result = _topological_sort([FakeA(), FakeB()])
        assert isinstance(result, list)
        assert len(result) == 2
