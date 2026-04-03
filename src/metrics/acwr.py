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
    requires = ["ctl", "atl"]

    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        atl = ctx.get_metric("atl", provider="runpulse:formula_v1")
        ctl = ctx.get_metric("ctl", provider="runpulse:formula_v1")
        if atl is None or ctl is None or ctl == 0:
            return []
        return [self._result(value=round(atl / ctl, 2))]
