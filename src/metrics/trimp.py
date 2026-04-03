"""TRIMP Calculator — 설계서 4-2 기준.

Banister (1991) TRIMPexp.
HR params: metric_store → activity_summaries → daily_wellness → fallback.
"""
from __future__ import annotations

import math

from src.metrics.base import CalcContext, CalcResult, MetricCalculator


class TRIMPCalculator(MetricCalculator):
    name = "trimp"
    provider = "runpulse:formula_v1"
    version = "banister_1991"
    scope_type = "activity"
    category = "rp_load"
    requires = []

    MALE_A = 1.92
    MALE_B = 0.64
    # TODO: config에서 성별 가져와 FEMALE_A=1.67, FEMALE_B=1.92 분기
    # TODO: config에서 성별 가져와 FEMALE_A=1.67, FEMALE_B=1.92 분기

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

        a, b = self.MALE_A, self.MALE_B
        trimp = duration_min * hr_reserve_frac * a * math.exp(b * hr_reserve_frac)

        confidence = 1.0
        if not self._has_measured_max_hr(ctx):
            confidence -= 0.2

        return [self._result(value=round(trimp, 1), confidence=confidence)]

    def _get_max_hr(self, ctx: CalcContext) -> int | None:
        stored = ctx.get_metric("max_hr_measured", scope_type="athlete", scope_id="me")
        if stored:
            return int(stored)
        activities = ctx.get_activities_in_range(days=180)
        max_hrs = [a["max_hr"] for a in activities if a.get("max_hr")]
        if max_hrs:
            return max(max_hrs)
        return 190

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
