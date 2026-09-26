"""LSI (Load Spike Index) Calculator — 설계서 4-3 기준.

LSI = 당일 부하 / 21일 롤링 평균. >1.5 = 급격한 부하 증가.
P7-PRED-89: 21일 중 부하 있는 날이 7일 미만이면 분모가 휴식기로 작아져 폭발한다(2024-06-28 LSI 101) → 산출하지 않음.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from src.metrics.base import CalcContext, CalcResult, MetricCalculator


class LSICalculator(MetricCalculator):
    name = "lsi"
    provider = "runpulse:formula_v1"
    version = "1.0"
    scope_type = "daily"
    category = "load"
    display_name = "부하 급증 지수 (LSI)"
    description = "당일 부하 / 21일 평균. >1.5면 급격한 부하 증가."
    unit = ""
    ranges = {"normal": [0, 1.3], "elevated": [1.3, 1.5], "spike": [1.5, 10]}
    higher_is_better = None
    decimal_places = 2
    display_name = "부하 급증 지수 (LSI)"
    description = "당일 부하 / 21일 평균. >1.5면 급격한 부하 증가."
    unit = ""
    ranges = {"normal": [0, 1.3], "elevated": [1.3, 1.5], "spike": [1.5, 10]}
    higher_is_better = None
    decimal_places = 2
    requires = ["trimp"]

    ROLLING_DAYS = 21
    MIN_ACTIVE_DAYS = 7    # (c) 주 2~3회 러너의 3주 최소 활동일

    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        date_str = ctx.scope_id
        today_load = self._get_day_load(ctx, date_str)
        if today_load == 0:
            return []

        target = datetime.strptime(date_str, "%Y-%m-%d")
        daily_loads = []
        for i in range(1, self.ROLLING_DAYS + 1):
            d = (target - timedelta(days=i)).strftime("%Y-%m-%d")
            daily_loads.append(self._get_day_load(ctx, d))

        avg_load = sum(daily_loads) / len(daily_loads) if daily_loads else 0
        if avg_load == 0 or sum(1 for x in daily_loads if x > 0) < self.MIN_ACTIVE_DAYS:
            return []

        return [self._result(value=round(today_load / avg_load, 2))]

    @staticmethod
    def _get_day_load(ctx, date_str) -> float:
        """특정 날짜의 TRIMP 합계 (prefetch 지원)."""
        return ctx.get_daily_load(date_str)
