"""Monotony & Strain Calculator — 설계서 4-3 기준.

Monotony = 7일 TRIMP 평균 / 표준편차. >2.0 = 과훈련 위험.
Strain = 7일 TRIMP 합계 × Monotony.
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta

from src.metrics.base import CalcContext, CalcResult, MetricCalculator
from src.metrics.lsi import LSICalculator


class MonotonyStrainCalculator(MetricCalculator):
    name = "monotony"
    provider = "runpulse:formula_v1"
    version = "1.0"
    scope_type = "daily"
    category = "rp_load"
    requires = ["trimp"]
    produces = ["monotony", "training_strain"]

    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        date_str = ctx.scope_id
        target = datetime.strptime(date_str, "%Y-%m-%d")

        loads = []
        for i in range(7):
            d = (target - timedelta(days=i)).strftime("%Y-%m-%d")
            loads.append(LSICalculator._get_day_load(ctx, d))

        if not loads or all(l == 0 for l in loads):
            return []

        mean = sum(loads) / len(loads)
        variance = sum((x - mean) ** 2 for x in loads) / len(loads)
        std = math.sqrt(variance)

        if std == 0:
            monotony = float("inf")
        else:
            monotony = mean / std

        strain = sum(loads) * monotony
        results = [self._result(value=round(monotony, 2), metric_name="monotony")]
        if not math.isinf(strain):
            results.append(self._result(value=round(strain, 1), metric_name="training_strain"))
        return results
