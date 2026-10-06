"""TRIMP 추정 Calculator — 심박 결측 활동의 부하를 페이스로 추정(DATA-CTL-WARMUP).

시기가 가까운 심박 보유 러닝에서 `avg_hr = a + b·speed` 를 회귀해 결측 활동의 평균 심박을 추정하고,
측정 TRIMP와 같은 Banister 식에 넣는다. metric_name은 `trimp`로 저장하되 provider가 낮은 우선순위
(`runpulse:rule_trimp_est`)라 측정값(formula_v1)이 있으면 항상 측정값이 primary가 된다.
"""
from __future__ import annotations

import math
from datetime import datetime

from src.metrics.base import CalcContext, CalcResult, MetricCalculator
from src.metrics.trimp import TRIMPCalculator

MIN_SAMPLES = 8
NEAREST_N = 60
HR_BOUNDS = (80.0, 200.0)


def _speed(act: dict) -> float | None:
    v = act.get("avg_speed_ms")
    if v:
        return float(v)
    dist, dur = act.get("distance_m"), act.get("duration_sec") or act.get("moving_time_sec")
    return dist / dur if dist and dur else None


def fit_hr_from_speed(samples: list[tuple[float, float]]) -> tuple[float, float] | None:
    """(speed, hr) 표본의 최소제곱 직선 (a, b). 분산 0이거나 기울기 ≤0이면 None."""
    n = len(samples)
    if n < 2:
        return None
    mx = sum(s for s, _ in samples) / n
    my = sum(h for _, h in samples) / n
    sxx = sum((s - mx) ** 2 for s, _ in samples)
    if sxx <= 0:
        return None
    b = sum((s - mx) * (h - my) for s, h in samples) / sxx
    return (my - b * mx, b) if b > 0 else None


class TRIMPEstCalculator(MetricCalculator):
    name = "trimp_est"
    produces = ["trimp"]
    provider = "runpulse:rule_trimp_est"
    version = "trimp_est_v1"
    scope_type = "activity"
    category = "load"
    display_name = "TRIMP (추정)"
    description = "심박 결측 러닝의 훈련 부하를 근접 시기 페이스-심박 관계로 추정한 값."
    unit = "AU"
    higher_is_better = None
    decimal_places = 0
    requires = []

    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        act = ctx.activity or {}
        if act.get("avg_hr") or "run" not in (act.get("activity_type") or "").lower():
            return []
        duration_sec = act.get("duration_sec") or act.get("moving_time_sec")
        speed = _speed(act)
        if not duration_sec or not speed:
            return []

        est_hr, conf = self._estimate_hr(ctx, act, speed)
        if est_hr is None:
            return []

        base = TRIMPCalculator()
        max_hr, rest_hr = base._get_max_hr(ctx), base._get_rest_hr(ctx)
        if not max_hr or not rest_hr or max_hr <= rest_hr:
            return []
        x = max(0.0, min(1.0, (est_hr - rest_hr) / (max_hr - rest_hr)))
        k, b = base.COEFFS[base._get_sex(ctx)]
        trimp = duration_sec / 60.0 * x * k * math.exp(b * x)
        return [self._result(value=round(trimp, 1), confidence=conf, metric_name="trimp")]

    def _estimate_hr(self, ctx: CalcContext, act: dict, speed: float):
        try:
            ref = datetime.fromisoformat(str(act.get("start_time"))[:19])
        except ValueError:
            return None, None
        pool = []
        for a in ctx.get_activities_in_range(3650, "running"):
            hr, sp = a.get("avg_hr"), _speed(a)
            if hr and sp and a.get("id") != act.get("id"):
                try:
                    gap = abs((datetime.fromisoformat(str(a["start_time"])[:19]) - ref).total_seconds())
                except ValueError:
                    continue
                pool.append((gap, sp, float(hr)))
        if len(pool) < MIN_SAMPLES:
            return None, None
        pool.sort(key=lambda t: t[0])
        near = [(s, h) for _, s, h in pool[:NEAREST_N]]
        fit = fit_hr_from_speed(near)
        if fit:
            hr, conf = fit[0] + fit[1] * speed, 0.4
        else:
            hr, conf = sum(h for _, h in near) / len(near), 0.25
        return max(HR_BOUNDS[0], min(HR_BOUNDS[1], hr)), conf
