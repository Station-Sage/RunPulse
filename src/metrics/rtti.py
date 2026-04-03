"""RTTI (Running Tolerance Training Index) — 달리기 내성 훈련 지수.

ATL / (CTL × wellness_factor) × 100
100 = 적정, >100 과부하, <70 여유.

v0.3 포팅: _v02_backup/rtti.py → MetricCalculator 형식
"""
from __future__ import annotations

from src.metrics.base import MetricCalculator, CalcResult, CalcContext


class RTTICalculator(MetricCalculator):
    name = "rtti"
    provider = "runpulse:formula_v1"
    version = "1.0"
    scope_type = "daily"
    category = "rp_load"
    requires = ["ctl", "atl"]
    produces = ["rtti"]

    display_name = "RTTI (훈련 내성 지수)"
    description = "ATL/CTL 기반 훈련 내성. 100=적정, >100 과부하, <70 여유."
    unit = "%"
    ranges = {"under": 70, "optimal": 100, "overload": 130, "danger": 160}
    higher_is_better = None
    format_type = "number"
    decimal_places = 1

    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        atl = ctx.get_metric("atl", provider="runpulse:formula_v1")
        ctl = ctx.get_metric("ctl", provider="runpulse:formula_v1")

        if atl is None and ctl is None:
            return []

        atl = float(atl) if atl is not None else 0.0
        ctl = float(ctl) if ctl is not None else 0.0

        if ctl <= 0 and atl <= 0:
            return []

        # 웰니스 보정
        wf = 1.0
        wellness = ctx.get_wellness()
        if wellness:
            bb = wellness.get("body_battery_high")
            if bb is not None:
                bb = float(bb)
                if bb < 30:
                    wf *= 0.8
                elif bb < 50:
                    wf *= 0.9
            sleep = wellness.get("sleep_score")
            if sleep is not None:
                sleep = float(sleep)
                if sleep < 40:
                    wf *= 0.85
                elif sleep < 60:
                    wf *= 0.92

        # CTL 기반 용량
        if ctl <= 0:
            capacity = max(atl * 0.5, 10.0)
        else:
            capacity = ctl * wf

        rtti = round(atl / capacity * 100, 1) if capacity > 0 else 0.0
        rtti = min(rtti, 200.0)

        return [self._result(
            value=rtti,
            json_val={
                "atl": round(atl, 1),
                "ctl": round(ctl, 1),
                "wellness_factor": round(wf, 2),
                "capacity": round(capacity, 1),
            },
        
            confidence=1.0,
        )]
