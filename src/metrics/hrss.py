"""HRSS Calculator — 설계서 4-2 기준.

HRSS = TRIMP / TRIMP_ref × 100 (1hr LTHR = 100).
"""
from __future__ import annotations

import math

from src.metrics.base import CalcContext, CalcResult, MetricCalculator
from src.metrics.trimp import TRIMPCalculator


class HRSSCalculator(MetricCalculator):
    name = "hrss"
    provider = "runpulse:formula_v1"
    version = "1.0"
    scope_type = "activity"
    category = "rp_load"
    requires = ["trimp"]

    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        trimp = ctx.get_metric("trimp", provider="runpulse:formula_v1")
        if trimp is None:
            return []

        lthr = ctx.get_metric("lactate_threshold_hr") or self._estimate_lthr(ctx)
        if not lthr:
            return []

        rest_hr = TRIMPCalculator()._get_rest_hr(ctx)
        max_hr = TRIMPCalculator()._get_max_hr(ctx)
        if not max_hr or max_hr <= rest_hr:
            return []

        hr_frac = (lthr - rest_hr) / (max_hr - rest_hr)
        trimp_lthr_1h = 60 * hr_frac * 1.92 * math.exp(0.64 * hr_frac)
        if trimp_lthr_1h == 0:
            return []

        hrss = (trimp / trimp_lthr_1h) * 100
        return [self._result(value=round(hrss, 1))]

    def _estimate_lthr(self, ctx):
        max_hr = TRIMPCalculator()._get_max_hr(ctx)
        return int(max_hr * 0.85) if max_hr else None
