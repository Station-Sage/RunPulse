"""RTTI (Running Tolerance Training Index) — 달리기 내성 훈련 지수.

ATL / (CTL × wellness_factor) × 100
100 = 적정, >100 과부하, <70 여유.
P7-PRED-89: CTL 이 형성되기 전(ACWR 과 같은 기준)엔 산출하지 않고, 200 절단을 없앴다(이전 15%가 0 또는 200에 포화).

v0.3 포팅: _v02_backup/rtti.py → MetricCalculator 형식
"""
from __future__ import annotations

from src.metrics.base import MetricCalculator, CalcResult, CalcContext


class RTTICalculator(MetricCalculator):
    name = "rtti"
    provider = "runpulse:formula_v1"
    version = "1.0"
    scope_type = "daily"
    category = "load"
    requires = ["ctl", "atl"]
    produces = ["rtti"]

    display_name = "RTTI (훈련 내성 지수)"
    description = "ATL/CTL 기반 훈련 내성. 100=적정, >100 과부하, <70 여유."
    unit = "%"
    ranges = {"under": [0, 70], "optimal": [70, 100], "overload": [100, 130], "danger": [130, 300]}
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

        from src.metrics.acwr import MIN_CTL, has_history
        if ctl < MIN_CTL or not has_history(ctx):
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
        capacity = ctl * wf
        rtti = round(atl / capacity * 100, 1)

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
