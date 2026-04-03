"""DI (Durability Index) — 설계서 4-4 기준.

장거리(90분+) 세션에서 후반부 페이스 유지 능력. 0~100.
"""
from __future__ import annotations

from src.metrics.base import CalcContext, CalcResult, MetricCalculator


class DICalculator(MetricCalculator):
    name = "di"
    provider = "runpulse:formula_v1"
    version = "1.0"
    scope_type = "daily"
    category = "rp_endurance"
    display_name = "내구성 지수 (DI)"
    description = "장거리 달리기에서 후반 페이스 유지 능력. 0~100."
    unit = "점"
    higher_is_better = True
    decimal_places = 1
    display_name = "내구성 지수 (DI)"
    description = "장거리 달리기에서 후반 페이스 유지 능력. 0~100."
    unit = "점"
    higher_is_better = True
    decimal_places = 1
    requires = []

    MIN_DURATION_SEC = 5400  # 90분

    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        activities = ctx.get_activities_in_range(days=56, activity_type="running")
        long_runs = [a for a in activities
                     if (a.get("moving_time_sec") or 0) >= self.MIN_DURATION_SEC]
        if not long_runs:
            return []

        ratios = []
        for act in long_runs:
            streams = ctx.get_streams(act["id"])
            if not streams or len(streams) < 120:
                continue
            mid = len(streams) // 2
            first_speeds = [s["speed_ms"] for s in streams[:mid]
                           if s.get("speed_ms") and s["speed_ms"] > 0]
            second_speeds = [s["speed_ms"] for s in streams[mid:]
                            if s.get("speed_ms") and s["speed_ms"] > 0]
            if first_speeds and second_speeds:
                avg_first = sum(first_speeds) / len(first_speeds)
                avg_second = sum(second_speeds) / len(second_speeds)
                if avg_first > 0:
                    ratios.append(avg_second / avg_first)

        if not ratios:
            return []

        avg_ratio = sum(ratios) / len(ratios)
        di = max(0, min(100, avg_ratio * 100))

        return [self._result(value=round(di, 1))]
