"""tests/test_pmc_trimp_v2.py — 부하 모델 재기준화(DECISIONS [P7-UX-REVIEW-0928] D1·D2) 회귀 테스트."""
import math
from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from src.metrics.base import CalcContext
from src.metrics.pmc import CTL_DAYS, LOAD_LOOKBACK_DAYS, PMCCalculator
from src.metrics.trimp import TRIMPCalculator

TARGET = date(2020, 6, 1)  # 과거 날짜 — 당일 경과 비율(frac) 영향 없음


def _pmc(loads: dict) -> dict:
    ctx = CalcContext(conn=None, scope_type="daily", scope_id=TARGET.isoformat(),
                      _prefetched_daily_loads=loads)
    return {r.metric_name: r.numeric_value for r in PMCCalculator().compute(ctx)}


def _steady(load: float, days: int, rest_last: int = 0) -> dict:
    return {(TARGET - timedelta(days=i)).isoformat(): load
            for i in range(rest_last, days)}


def test_rest_day_decays_ctl_by_one_over_tau():
    """부하 0인 날 CTL 감소량 = 전날 CTL / 42 (원문 재귀식)."""
    out = _pmc(_steady(60.0, LOAD_LOOKBACK_DAYS, rest_last=1))
    ctl, ramp = out["ctl"], out["ramp_rate"]
    prev = ctl - ramp
    assert ramp == pytest.approx(-prev / CTL_DAYS, abs=0.02)


def test_long_window_reaches_steady_state():
    """6τ 창이면 일정 부하에서 CTL이 부하의 99% 이상(창 절단 과소 산출 제거)."""
    out = _pmc(_steady(60.0, LOAD_LOOKBACK_DAYS + 1))
    assert out["ctl"] >= 59.4
    assert out["atl"] == pytest.approx(60.0, abs=0.1)


def test_no_load_returns_empty():
    assert _pmc({}) == {}


def _trimp(sex: str, avg_hr=160, rest=50, max_hr=190, minutes=60):
    act = {"avg_hr": avg_hr, "duration_sec": minutes * 60, "start_time": "2020-06-01T08:00:00"}
    ctx = SimpleNamespace(
        activity=act,
        get_athlete_sex=lambda: sex,
        get_metric=lambda *a, **k: max_hr,
        get_wellness=lambda d=None: {"resting_hr": rest},
        get_daily_metric_series=lambda *a, **k: [],
        get_activities_in_range=lambda *a, **k: [],
    )
    return TRIMPCalculator().compute(ctx)[0].numeric_value


@pytest.mark.parametrize("sex, k, b", [("male", 0.64, 1.92), ("female", 0.86, 1.67)])
def test_trimp_banister_coefficients(sex, k, b):
    x = (160 - 50) / (190 - 50)
    expected = 60 * x * k * math.exp(b * x)
    assert _trimp(sex) == pytest.approx(expected, abs=0.1)
