"""RMR (Recovery & Metabolic Readiness) — 설계서 4-4 기준.

복합 회복 상태 점수 (0~100). 웰니스 + 피트니스 지표 종합.
"""
from __future__ import annotations

from src.metrics.base import CalcContext, CalcResult, MetricCalculator


class RMRCalculator(MetricCalculator):
    name = "rmr"
    provider = "runpulse:formula_v1"
    version = "1.0"
    scope_type = "daily"
    category = "rp_recovery"
    display_name = "회복 준비도 (RMR)"
    description = "안정심박, 체력배터리, TSB, 수면을 종합한 회복 상태."
    unit = "점"
    ranges = {"poor": [0, 30], "low": [30, 50], "moderate": [50, 70], "good": [70, 85], "excellent": [85, 100]}
    higher_is_better = True
    decimal_places = 1
    display_name = "회복 준비도 (RMR)"
    description = "안정심박, 체력배터리, TSB, 수면을 종합한 회복 상태."
    unit = "점"
    ranges = {"poor": [0, 30], "low": [30, 50], "moderate": [50, 70], "good": [70, 85], "excellent": [85, 100]}
    higher_is_better = True
    decimal_places = 1
    requires = ["tsb"]

    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        wellness = ctx.get_wellness()
        components = {}
        total_w = 0.0

        rhr = wellness.get("resting_hr")
        if rhr is not None:
            rhr_score = max(0, min(100, (80 - rhr) / 30 * 100))
            components["resting_hr"] = rhr_score
            total_w += 0.25

        bb = wellness.get("body_battery_high")
        if bb is not None:
            components["body_battery"] = min(bb, 100)
            total_w += 0.25

        tsb = ctx.get_metric("tsb", provider="runpulse:formula_v1")
        if tsb is not None:
            tsb_score = max(0, min(100, (tsb + 30) / 60 * 100))
            components["tsb"] = tsb_score
            total_w += 0.25

        sleep = wellness.get("sleep_score")
        if sleep is not None:
            components["sleep"] = min(sleep, 100)
            total_w += 0.25

        if not components or total_w == 0:
            return []

        weights = {"resting_hr": 0.25, "body_battery": 0.25, "tsb": 0.25, "sleep": 0.25}
        score = sum(components[k] * weights[k] for k in components) / total_w

        return [self._result(
            value=round(score, 1),
            json_val={"components": {k: round(v, 1) for k, v in components.items()}},
        )]
