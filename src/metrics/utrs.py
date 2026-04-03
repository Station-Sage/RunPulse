"""UTRS (Unified Training Readiness Score) — 설계서 4-4 기준.

0~100. 가중치: body_battery×0.30 + TSB×0.25 + sleep×0.20 + HRV×0.15 + stress×0.10
가용 데이터만으로 가중 평균 (재정규화).
"""
from __future__ import annotations

from src.metrics.base import CalcContext, CalcResult, MetricCalculator


class UTRSCalculator(MetricCalculator):
    name = "utrs"
    provider = "runpulse:formula_v1"
    version = "pdf_weights_v1"
    scope_type = "daily"
    category = "rp_readiness"
    requires = ["tsb"]

    WEIGHTS = {
        "body_battery": 0.30,
        "tsb": 0.25,
        "sleep": 0.20,
        "hrv": 0.15,
        "stress": 0.10,
    }

    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        wellness = ctx.get_wellness()
        components = {}
        total_weight = 0.0

        bb = wellness.get("body_battery_high")
        if bb is not None:
            components["body_battery"] = self._norm(bb, 0, 100)
            total_weight += self.WEIGHTS["body_battery"]

        tsb = ctx.get_metric("tsb", provider="runpulse:formula_v1")
        if tsb is None:
            tsb = ctx.get_metric("tsb")
        if tsb is not None:
            components["tsb"] = self._norm(tsb + 30, 0, 60)
            total_weight += self.WEIGHTS["tsb"]

        sleep = wellness.get("sleep_score")
        if sleep is not None:
            components["sleep"] = self._norm(sleep, 0, 100)
            total_weight += self.WEIGHTS["sleep"]

        hrv = wellness.get("hrv_weekly_avg")
        if hrv is not None:
            components["hrv"] = self._norm(hrv, 20, 100)
            total_weight += self.WEIGHTS["hrv"]

        stress = wellness.get("avg_stress")
        if stress is not None:
            components["stress"] = self._norm(100 - stress, 0, 100)
            total_weight += self.WEIGHTS["stress"]

        if not components or total_weight == 0:
            return []

        score = sum(
            components[k] * self.WEIGHTS[k] for k in components
        ) / total_weight

        confidence = min(total_weight / sum(self.WEIGHTS.values()), 1.0)

        return [self._result(
            value=round(score, 1),
            confidence=round(confidence, 2),
            json_val={"components": {k: round(v, 1) for k, v in components.items()}},
        )]

    @staticmethod
    def _norm(val, lo, hi) -> float:
        if hi == lo:
            return 50.0
        return max(0.0, min(100.0, (val - lo) / (hi - lo) * 100))
