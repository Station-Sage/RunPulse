"""CIRS (Composite Injury Risk Score) — 설계서 4-4 기준.

ACWR 편차 + Monotony + LSI + 수면/HRV 악화 신호 → 0~100 위험도.
"""
from __future__ import annotations

from src.metrics.base import CalcContext, CalcResult, MetricCalculator


class CIRSCalculator(MetricCalculator):
    name = "cirs"
    provider = "runpulse:formula_v1"
    version = "1.0"
    scope_type = "daily"
    category = "rp_injury"
    requires = ["acwr", "monotony", "lsi"]

    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        components = {}
        total_weight = 0.0

        acwr = ctx.get_metric("acwr", provider="runpulse:formula_v1")
        if acwr is not None:
            acwr_risk = abs(acwr - 1.0) * 100
            acwr_risk = min(acwr_risk, 100)
            components["acwr"] = acwr_risk
            total_weight += 0.35

        monotony = ctx.get_metric("monotony", provider="runpulse:formula_v1")
        if monotony is not None:
            mono_risk = min((monotony / 2.0) * 50, 100)
            components["monotony"] = mono_risk
            total_weight += 0.25

        lsi = ctx.get_metric("lsi", provider="runpulse:formula_v1")
        if lsi is not None:
            lsi_risk = min(max(lsi - 1.0, 0) * 100, 100)
            components["lsi"] = lsi_risk
            total_weight += 0.20

        wellness = ctx.get_wellness()
        sleep = wellness.get("sleep_score")
        if sleep is not None:
            sleep_risk = max(0, 100 - sleep)
            components["sleep"] = sleep_risk
            total_weight += 0.10

        hrv = wellness.get("hrv_weekly_avg")
        if hrv is not None:
            hrv_risk = max(0, min(100, (60 - hrv) / 40 * 100))
            components["hrv"] = hrv_risk
            total_weight += 0.10

        if not components or total_weight == 0:
            return []

        weights = {"acwr": 0.35, "monotony": 0.25, "lsi": 0.20, "sleep": 0.10, "hrv": 0.10}
        score = sum(components[k] * weights[k] for k in components) / total_weight
        confidence = round(min(total_weight / 1.0, 1.0), 2)

        return [self._result(
            value=round(score, 1),
            confidence=confidence,
            json_val={"components": {k: round(v, 1) for k, v in components.items()}},
        )]
