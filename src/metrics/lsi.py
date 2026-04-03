"""LSI (Load Spike Index) Calculator — 설계서 4-3 기준.

LSI = 당일 부하 / 21일 롤링 평균. >1.5 = 급격한 부하 증가.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from src.metrics.base import CalcContext, CalcResult, MetricCalculator


class LSICalculator(MetricCalculator):
    name = "lsi"
    provider = "runpulse:formula_v1"
    version = "1.0"
    scope_type = "daily"
    category = "rp_load"
    requires = ["trimp"]

    ROLLING_DAYS = 21

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
        if avg_load == 0:
            return []

        return [self._result(value=round(today_load / avg_load, 2))]

    @staticmethod
    def _get_day_load(ctx, date_str) -> float:
        rows = ctx.conn.execute("""
            SELECT m.numeric_value
            FROM metric_store m
            JOIN v_canonical_activities a ON CAST(m.scope_id AS INTEGER) = a.id
            WHERE m.scope_type = 'activity'
            AND m.metric_name = 'trimp' AND m.is_primary = 1
            AND substr(a.start_time, 1, 10) = ?
        """, [date_str]).fetchall()
        return sum(r[0] or 0 for r in rows)
