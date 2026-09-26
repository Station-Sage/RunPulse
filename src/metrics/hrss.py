"""HRSS Calculator — 설계서 4-2 기준.

HRSS = TRIMP / TRIMP_ref × 100 (1hr LTHR = 100).
P7-PRED-89: LTHR 을 hr_profile 자체 추정(lthr_self)에서 읽는다. 이전엔 항상 0.85·HRmax 로 추정해 TRIMP 의 상수배(1.54)였다.
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
    category = "load"
    display_name = "HRSS"
    description = "TRIMP을 젖산역치 심박으로 정규화한 스트레스 점수. 1시간 LTHR 운동 = 100."
    unit = "점"
    higher_is_better = None
    display_name = "HRSS"
    description = "TRIMP을 젖산역치 심박으로 정규화한 스트레스 점수. 1시간 LTHR 운동 = 100."
    unit = "점"
    higher_is_better = None
    requires = ["trimp"]

    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        trimp = ctx.get_metric("trimp", provider="runpulse:formula_v1")
        if trimp is None:
            return []

        day = ((ctx.activity or {}).get("start_time") or "")[:10] if getattr(ctx, "conn", None) is not None else ""
        lthr = (ctx.get_metric("lactate_threshold_hr")
                or (ctx.get_latest_daily_metric("lthr_self", day) if day else None) or self._estimate_lthr(ctx))
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
        return round(max_hr * 0.917, 1) if max_hr else None      # hr_profile 폴백과 같은 비율
