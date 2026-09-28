"""TRIMP Calculator — 설계서 4-2 기준.

Banister (1991) TRIMPexp.
HR params: metric_store → activity_summaries → daily_wellness → fallback.
"""
from __future__ import annotations

import math

from src.metrics.base import CalcContext, CalcResult, MetricCalculator
from src.metrics.stream_utils import athlete_max_hr


class TRIMPCalculator(MetricCalculator):
    name = "trimp"
    provider = "runpulse:formula_v1"
    version = "banister_1991_v2"
    scope_type = "activity"
    category = "load"
    display_name = "TRIMP (Banister)"
    description = "심박 기반 훈련 부하 점수. 운동 시간과 심박 강도를 종합한 부하 지표."
    unit = "AU"
    ranges = {"recovery": [0, 50], "easy": [50, 100], "moderate": [100, 200], "hard": [200, 350], "very_hard": [350, 999]}
    higher_is_better = None
    decimal_places = 0
    display_name = "TRIMP (Banister)"
    description = "심박 기반 훈련 부하 점수. 운동 시간과 심박 강도를 종합한 부하 지표."
    unit = "AU"
    ranges = {"recovery": [0, 50], "easy": [50, 100], "moderate": [100, 200], "hard": [200, 350], "very_hard": [350, 999]}
    higher_is_better = None
    decimal_places = 0
    requires = []

    # Banister TRIMPexp = 시간(분) × x × k × e^(b·x). 남 k=0.64, b=1.92 / 여 k=0.86, b=1.67.
    # v1은 k와 b가 뒤바뀌어 1.92·e^(0.64x)로 계산했다(고강도 가중이 약해짐, DECISIONS D2).
    COEFFS = {"male": (0.64, 1.92), "female": (0.86, 1.67)}

    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        act = ctx.activity
        avg_hr = act.get("avg_hr")
        duration_sec = act.get("duration_sec") or act.get("moving_time_sec")
        if not avg_hr or not duration_sec:
            return []

        max_hr = self._get_max_hr(ctx)
        rest_hr = self._get_rest_hr(ctx)
        if not max_hr or not rest_hr or max_hr <= rest_hr:
            return []

        duration_min = duration_sec / 60.0
        hr_reserve_frac = (avg_hr - rest_hr) / (max_hr - rest_hr)
        hr_reserve_frac = max(0.0, min(1.0, hr_reserve_frac))

        k, b = self.COEFFS[self._get_sex(ctx)]
        trimp = duration_min * hr_reserve_frac * k * math.exp(b * hr_reserve_frac)

        confidence = 1.0
        if not self._has_measured_max_hr(ctx):
            confidence -= 0.2

        return [self._result(value=round(trimp, 1), confidence=confidence)]

    def _get_sex(self, ctx: CalcContext) -> str:
        getter = getattr(ctx, "get_athlete_sex", None)
        sex = getter() if getter else "male"
        return sex if sex in self.COEFFS else "male"

    def _get_max_hr(self, ctx: CalcContext) -> int | None:
        return athlete_max_hr(ctx)

    def _get_rest_hr(self, ctx: CalcContext) -> int | None:
        act = ctx.activity
        date = act.get("start_time", "")[:10]
        wellness = ctx.get_wellness(date)
        if wellness.get("resting_hr"):
            return int(wellness["resting_hr"])
        recent = ctx.get_daily_metric_series("resting_hr", days=7)
        if recent:
            return int(sum(v for _, v in recent) / len(recent))
        return 60

    def _has_measured_max_hr(self, ctx: CalcContext) -> bool:
        return ctx.get_metric("max_hr_measured", scope_type="athlete", scope_id="me") is not None
