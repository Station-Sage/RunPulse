"""ACWR Calculator — 설계서 4-3 기준.

ACWR = ATL / CTL. 최적 범위: 0.8~1.3.
"""
from __future__ import annotations

from src.metrics.base import CalcContext, CalcResult, MetricCalculator


class ACWRCalculator(MetricCalculator):
    name = "acwr"
    provider = "runpulse:formula_v1"
    version = "1.0"
    scope_type = "daily"
    category = "rp_load"
    display_name = "ACWR"
    description = "급성:만성 부하 비율. 최적 범위 0.8~1.3."
    unit = ""
    ranges = {"low": [0, 0.8], "optimal": [0.8, 1.3], "caution": [1.3, 1.5], "danger": [1.5, 5]}
    higher_is_better = None
    decimal_places = 2
    display_name = "ACWR"
    description = "급성:만성 부하 비율. 최적 범위 0.8~1.3."
    unit = ""
    ranges = {"low": [0, 0.8], "optimal": [0.8, 1.3], "caution": [1.3, 1.5], "danger": [1.5, 5]}
    higher_is_better = None
    decimal_places = 2
    requires = ["ctl", "atl"]

    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        atl = ctx.get_metric("atl", provider="runpulse:formula_v1")
        ctl = ctx.get_metric("ctl", provider="runpulse:formula_v1")
        if atl is None or ctl is None or ctl == 0:
            return []
        return [self._result(value=round(atl / ctl, 2))]
