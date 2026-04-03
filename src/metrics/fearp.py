"""FEARP (Fitness & Environment Adjusted Running Pace) — 설계서 4-4 기준.

실제 페이스를 기온/습도/고도로 보정한 환경 보정 페이스.
"""
from __future__ import annotations

from src.metrics.base import CalcContext, CalcResult, MetricCalculator


class FEARPCalculator(MetricCalculator):
    name = "fearp"
    provider = "runpulse:formula_v1"
    version = "1.0"
    scope_type = "activity"
    category = "rp_performance"
    requires = []

    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        act = ctx.activity
        if act.get("activity_type") not in ("running", "trail_running", "treadmill"):
            return []

        pace = act.get("avg_pace_sec_km")
        if not pace or pace <= 0:
            speed = act.get("avg_speed_ms")
            if speed and speed > 0:
                pace = 1000.0 / speed
            else:
                return []

        temp = act.get("avg_temperature")
        elevation = act.get("elevation_gain") or 0
        distance_m = act.get("distance_m") or 0

        adjustment = 1.0

        if temp is not None:
            if temp > 15:
                adjustment += (temp - 15) * 0.005
            elif temp < 5:
                adjustment += (5 - temp) * 0.003

        if distance_m > 0 and elevation > 0:
            grade_pct = (elevation / distance_m) * 100
            adjustment += grade_pct * 0.02

        humidity = ctx.get_metric("weather_humidity_pct")
        if humidity is not None and humidity > 60:
            adjustment += (humidity - 60) * 0.001

        fearp = pace / adjustment

        return [self._result(value=round(fearp, 1))]
