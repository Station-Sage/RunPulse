"""VDOT Calculator — 설계서 4-2 기준.

Jack Daniels (2005) VDOT from distance/time.
"""
from __future__ import annotations

import math

from src.metrics.base import CalcContext, CalcResult, MetricCalculator


class VDOTCalculator(MetricCalculator):
    name = "runpulse_vdot"
    provider = "runpulse:formula_v1"
    version = "daniels_2005"
    scope_type = "activity"
    category = "rp_performance"
    requires = []

    MINIMUM_DISTANCE_M = 1500
    MINIMUM_DURATION_SEC = 300
    MAXIMUM_DURATION_SEC = 14400

    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        act = ctx.activity
        if act.get("activity_type") not in ("running", "trail_running", "treadmill", "race"):
            return []

        distance_m = act.get("distance_m") or 0
        duration_sec = act.get("moving_time_sec") or act.get("duration_sec") or 0

        if (distance_m < self.MINIMUM_DISTANCE_M
                or duration_sec < self.MINIMUM_DURATION_SEC
                or duration_sec > self.MAXIMUM_DURATION_SEC):
            return []

        velocity = distance_m / duration_sec  # m/s
        time_min = duration_sec / 60.0
        v_mpm = velocity * 60

        vo2 = -4.60 + 0.182258 * v_mpm + 0.000104 * v_mpm * v_mpm
        pct_max = (0.8
                   + 0.1894393 * math.exp(-0.012778 * time_min)
                   + 0.2989558 * math.exp(-0.1932605 * time_min))
        if pct_max <= 0:
            return []

        vdot = vo2 / pct_max

        confidence = 0.9
        if act.get("activity_type") == "treadmill":
            confidence -= 0.1
        if distance_m < 3000:
            confidence -= 0.1

        return [self._result(value=round(vdot, 1), confidence=confidence)]
