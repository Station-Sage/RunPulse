"""Aerobic Decoupling Calculator — 설계서 4-2 기준.

Decoupling = (EF_first_half - EF_second_half) / EF_first_half × 100
EF = avg_speed / avg_hr
< 5% = good aerobic fitness
"""
from __future__ import annotations

from src.metrics.base import CalcContext, CalcResult, MetricCalculator


class AerobicDecouplingCalculator(MetricCalculator):
    name = "aerobic_decoupling_rp"
    provider = "runpulse:formula_v1"
    version = "1.0"
    scope_type = "activity"
    category = "rp_efficiency"
    requires = []

    MINIMUM_DURATION_SEC = 1200  # 20분

    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        act = ctx.activity
        duration = act.get("moving_time_sec") or act.get("duration_sec")
        if not duration or duration < self.MINIMUM_DURATION_SEC:
            return []

        streams = ctx.get_streams()
        if not streams or len(streams) < 120:
            return []

        mid = len(streams) // 2
        ef_first = self._calc_ef(streams[:mid])
        ef_second = self._calc_ef(streams[mid:])

        if ef_first is None or ef_second is None or ef_first == 0:
            return []

        decoupling = (ef_first - ef_second) / ef_first * 100
        return [self._result(value=round(decoupling, 2))]

    def _calc_ef(self, segment: list[dict]) -> float | None:
        speeds = [s["speed_ms"] for s in segment
                  if s.get("speed_ms") and s["speed_ms"] > 0]
        hrs = [s["heart_rate"] for s in segment
               if s.get("heart_rate") and s["heart_rate"] > 60]
        if not speeds or not hrs:
            return None
        avg_speed = sum(speeds) / len(speeds)
        avg_hr = sum(hrs) / len(hrs)
        return avg_speed / avg_hr if avg_hr > 0 else None
