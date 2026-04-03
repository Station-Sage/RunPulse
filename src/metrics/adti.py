"""ADTI (Adaptive Training Trend Index) — 설계서 4-4 기준.

4주간 CTL 변화율 + 부하 패턴 → 훈련 적응 방향 (-100 ~ +100).
"""
from __future__ import annotations

from src.metrics.base import CalcContext, CalcResult, MetricCalculator


class ADTICalculator(MetricCalculator):
    name = "adti"
    provider = "runpulse:formula_v1"
    version = "1.0"
    scope_type = "daily"
    category = "rp_trend"
    display_name = "훈련 추세 (ADTI)"
    description = "28일간 CTL 변화율. 양수=상승, 음수=하락."
    unit = ""
    ranges = {"declining": [-100, -10], "stable": [-10, 10], "building": [10, 100]}
    higher_is_better = True
    decimal_places = 1
    display_name = "훈련 추세 (ADTI)"
    description = "28일간 CTL 변화율. 양수=상승, 음수=하락."
    unit = ""
    ranges = {"declining": [-100, -10], "stable": [-10, 10], "building": [10, 100]}
    higher_is_better = True
    decimal_places = 1
    requires = ["ctl"]

    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        series = ctx.get_daily_metric_series("ctl", days=28, provider="runpulse:formula_v1")
        if len(series) < 14:
            return []

        values = [v for _, v in series]
        first_half = values[:len(values)//2]
        second_half = values[len(values)//2:]

        avg_first = sum(first_half) / len(first_half) if first_half else 0
        avg_second = sum(second_half) / len(second_half) if second_half else 0

        if avg_first == 0:
            return []

        change_pct = ((avg_second - avg_first) / avg_first) * 100
        adti = max(-100, min(100, change_pct * 5))

        return [self._result(value=round(adti, 1))]
