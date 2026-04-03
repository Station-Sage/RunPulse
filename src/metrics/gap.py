"""GAP (Grade Adjusted Pace) Calculator — 설계서 4-2 기준.

Minetti (2002) 에너지 비용 모델.
"""
from __future__ import annotations

from src.metrics.base import CalcContext, CalcResult, MetricCalculator


class GAPCalculator(MetricCalculator):
    name = "gap_rp"
    provider = "runpulse:formula_v1"
    version = "minetti_2002"
    scope_type = "activity"
    category = "rp_performance"
    needs_streams = True
    requires = []

    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        streams = ctx.get_streams()
        if not streams or len(streams) < 60:
            return []

        total_adj_dist = 0.0
        total_time = 0.0

        for i in range(1, len(streams)):
            prev, curr = streams[i - 1], streams[i]
            dt = (curr.get("elapsed_sec") or 0) - (prev.get("elapsed_sec") or 0)
            if dt <= 0:
                continue
            speed = curr.get("speed_ms")
            if speed is None or speed <= 0:
                continue

            grade_frac = (curr.get("grade_pct") or 0) / 100.0
            ef = self._grade_effort_factor(grade_frac)
            total_adj_dist += (speed * dt) / ef
            total_time += dt

        if total_time == 0 or total_adj_dist == 0:
            return []

        gap_speed = total_adj_dist / total_time
        gap_pace = 1000.0 / gap_speed if gap_speed > 0 else None
        if gap_pace is None:
            return []

        return [self._result(value=round(gap_pace, 1))]

    @staticmethod
    def _grade_effort_factor(grade: float) -> float:
        cost = (155.4 * grade**5
                - 30.4 * grade**4
                - 43.3 * grade**3
                + 46.3 * grade**2
                + 19.5 * grade
                + 3.6)
        if cost <= 0:
            cost = 0.5
        return cost / 3.6
