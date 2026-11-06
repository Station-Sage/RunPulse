"""training_balance_axes: score clamp·band 경계·target 우선순위·A6 부분 결측·state (balance-radar §3·§8 T2)."""
from datetime import date, timedelta

import pytest

from src.services import training_balance_axes as ax

AS_OF = "2026-11-06"


def test_score_clamp_and_missing():
    assert ax.score(35.5, 40) == 88.8
    assert ax.score(100, 10) == 150.0          # 1.5 상한
    assert ax.score(-1, 10) == 0.0
    assert ax.score(None, 10) is None and ax.score(5, None) is None and ax.score(5, 0) is None


@pytest.mark.parametrize("v,exp", [(79.9, "low"), (80, "balanced"), (120, "balanced"), (120.1, "high"), (None, None)])
def test_status_band_edges_inclusive(v, exp):
    assert ax.status(v, (80, 120)) == exp


def test_build_axis_reason_cleared_when_scored_and_stale():
    a = ax.build_axis("easy_base", AS_OF, 83.1, 80.0, "default_rule", reason="insufficient_runs",
                      source=["tids"], computed_on="2026-11-04")
    assert a["score"] == 103.9 and a["status"] == "balanced" and a["reason"] is None and a["stale"] is True
    b = ax.build_axis("load", AS_OF, None, 1.0, "default_rule", reason="acwr_warmup", computed_on=None)
    assert b["score"] is None and b["status"] is None and b["reason"] == "acwr_warmup" and b["reason_text"]
    assert b["stale"] is False and b["label"] == "부하 균형"


def _hist(weeks: int, km: float = 30.0, peak: float | None = None) -> list[tuple[str, float]]:
    d0 = date.fromisoformat(AS_OF)
    out = [((d0 - timedelta(days=7 * i)).isoformat(), km) for i in range(weeks)]
    if peak is not None:
        out[-1] = (out[-1][0], peak)
    return out


def test_volume_target_priority_plan_then_peak():
    plan = {"2026-10-12": 40, "2026-10-19": 42, "2026-10-26": 44, "2026-11-02": 46}
    assert ax.volume_target(plan, _hist(10)) == (43.0, "plan", None)
    three = dict(list(plan.items())[:3])           # 계획 주 3개 → 개인 최고로
    assert ax.volume_target(three, _hist(10, peak=40)) == (40, "personal_peak", None)
    assert ax.volume_target({}, _hist(7)) == (None, None, "insufficient_history")


def test_goal_long_run_table():
    assert [ax.goal_long_run_km(d) for d in (42.195, 21.1, 10, 5, None)] == [30.0, 18.0, 14.0, 12.0, None]


def test_long_run_target_priority():
    assert ax.long_run_target(32, 42.195, 40) == (32, "plan")
    assert ax.long_run_target(None, 42.195, 40) == (30.0, "goal")
    assert ax.long_run_target(None, None, 40) == (12.0, "default_rule")
    assert ax.long_run_target(None, None, None) == (10.0, "default_rule")


def _wellness(days: int, sleep=None, hrv=None, stress=None):
    d0 = date.fromisoformat(AS_OF)
    dates = [(d0 - timedelta(days=days - 1 - i)).isoformat() for i in range(days)]
    def col(f):
        return [f(i, days) if f else None for i in range(days)]
    return dates, {"sleep_score": col(sleep), "hrv_last_night": col(hrv), "avg_stress": col(stress)}


def test_recovery_ratio_partial_items_and_inverse_stress():
    # 최근 7일 수면 90, 이전 70 → m7/m60 > 1. HRV 없음. 스트레스 최근 낮음 → 역수 > 1.
    dates, s = _wellness(60, sleep=lambda i, n: 90 if i >= n - 7 else 70, stress=lambda i, n: 20 if i >= n - 7 else 40)
    v, last = ax.recovery_ratio(dates, s, AS_OF)
    m60_sleep = (90 * 7 + 70 * 53) / 60
    m60_stress = (20 * 7 + 40 * 53) / 60
    assert v == pytest.approx((90 / m60_sleep + m60_stress / 20) / 2)
    assert last == AS_OF


def test_recovery_ratio_insufficient_days():
    dates, s = _wellness(29, sleep=lambda i, n: 70)          # 60일 중 <30일
    assert ax.recovery_ratio(dates, s, AS_OF) == (None, None)
    dates, s = _wellness(60, sleep=lambda i, n: 70 if i < n - 4 else None)  # 최근 7일 중 3일
    assert ax.recovery_ratio(dates, s, AS_OF) == (None, None)


def test_recovery_ignores_future_dates():
    dates, s = _wellness(60, sleep=lambda i, n: 70)
    dates += ["2026-11-07"]
    s["sleep_score"] += [10]
    assert ax.recovery_ratio(dates, s, AS_OF)[0] == pytest.approx(1.0)


@pytest.mark.parametrize("n,exp", [(3, "collecting"), (4, "partial"), (5, "partial"), (6, "ready")])
def test_overall_state(n, exp):
    axes = [{"score": 100.0 if i < n else None} for i in range(6)]
    assert ax.overall_state(axes) == exp
