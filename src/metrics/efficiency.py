"""Efficiency Factor Calculator — 설계서 4-2 기준.

EF = avg_speed / avg_hr × 1000
"""
from __future__ import annotations

from src.metrics.base import CalcContext, CalcResult, MetricCalculator


class EfficiencyFactorCalculator(MetricCalculator):
    name = "efficiency_factor_rp"
    provider = "runpulse:formula_v1"
    version = "1.0"
    scope_type = "activity"
    category = "rp_efficiency"
    display_name = "효율 계수 (EF)"
    description = "평균속도/평균심박 × 1000. 높을수록 효율적."
    unit = ""
    higher_is_better = True
    decimal_places = 2
    display_name = "효율 계수 (EF)"
    description = "평균속도/평균심박 × 1000. 높을수록 효율적."
    unit = ""
    higher_is_better = True
    decimal_places = 2
    requires = []

    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        act = ctx.activity
        avg_speed = act.get("avg_speed_ms")
        avg_hr = act.get("avg_hr")
        if not avg_speed or not avg_hr or avg_hr == 0:
            return []
        ef_display = round((avg_speed / avg_hr) * 1000, 2)
        return [self._result(value=ef_display)]
