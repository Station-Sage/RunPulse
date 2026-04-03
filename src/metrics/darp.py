"""DARP (Dynamic Adjusted Race Prediction) — 설계서 4-4 기준.

VDOT + DI + EF 기반 레이스 예측 시간 (초).
"""
from __future__ import annotations

import math

from src.metrics.base import CalcContext, CalcResult, MetricCalculator


class DARPCalculator(MetricCalculator):
    name = "darp"
    provider = "runpulse:formula_v1"
    version = "1.0"
    scope_type = "daily"
    category = "rp_prediction"
    requires = ["runpulse_vdot"]
    produces = ["darp_5k", "darp_10k", "darp_half", "darp_marathon"]

    DISTANCES = {
        "darp_5k": 5000,
        "darp_10k": 10000,
        "darp_half": 21097.5,
        "darp_marathon": 42195,
    }

    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        recent_acts = ctx.get_activities_in_range(days=30, activity_type="running")
        vdots = []
        for act in recent_acts:
            v = ctx.get_activity_metric(act["id"], "runpulse_vdot")
            if v and v > 20:
                vdots.append(v)

        if not vdots:
            return []

        avg_vdot = sum(vdots) / len(vdots)

        di = ctx.get_metric("di", provider="runpulse:formula_v1")
        ef_adj = 1.0
        if di is not None and di < 90:
            ef_adj += (90 - di) * 0.002

        results = []
        for name, dist in self.DISTANCES.items():
            pred_sec = self._predict_time(avg_vdot, dist) * ef_adj
            results.append(self._result(value=round(pred_sec, 0), metric_name=name))

        return results

    @staticmethod
    def _predict_time(vdot: float, distance_m: float) -> float:
        v_mpm = (vdot * 0.8 + 4.60) / (0.182258 + 0.000104 * 200)
        velocity_ms = max(v_mpm / 60, 1.0)
        return distance_m / velocity_ms
