"""PMC (ATL/CTL/TSB/Ramp Rate) Calculator — 설계서 4-3 기준.

ATL = 7일 EMA, CTL = 42일 EMA, TSB = CTL - ATL.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from src.metrics.base import CalcContext, CalcResult, MetricCalculator


class PMCCalculator(MetricCalculator):
    name = "ctl"
    provider = "runpulse:formula_v1"
    version = "1.0"
    scope_type = "daily"
    category = "rp_load"
    display_name = "PMC (ATL/CTL/TSB)"
    description = "Performance Management Chart. 42일 만성부하(CTL), 7일 급성부하(ATL), 훈련균형(TSB)."
    unit = "AU"
    higher_is_better = None
    display_name = "PMC (ATL/CTL/TSB)"
    description = "Performance Management Chart. 42일 만성부하(CTL), 7일 급성부하(ATL), 훈련균형(TSB)."
    unit = "AU"
    higher_is_better = None
    requires = ["trimp"]
    produces = ["ctl", "atl", "tsb", "ramp_rate"]

    ATL_DAYS = 7
    CTL_DAYS = 42

    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        date_str = ctx.scope_id
        daily_loads = self._get_daily_loads(ctx, days=self.CTL_DAYS + 7)
        if not daily_loads:
            return []

        atl_decay = 2.0 / (self.ATL_DAYS + 1)
        ctl_decay = 2.0 / (self.CTL_DAYS + 1)
        atl = 0.0
        ctl = 0.0
        prev_ctl = None

        target = datetime.strptime(date_str, "%Y-%m-%d")
        current = target - timedelta(days=self.CTL_DAYS + 7)

        while current <= target:
            ds = current.strftime("%Y-%m-%d")
            load = daily_loads.get(ds, 0)
            atl = atl * (1 - atl_decay) + load * atl_decay
            prev_ctl = ctl
            ctl = ctl * (1 - ctl_decay) + load * ctl_decay
            current += timedelta(days=1)

        tsb = ctl - atl
        ramp_rate = ctl - prev_ctl if prev_ctl is not None else 0

        return [
            self._result(value=round(ctl, 1), metric_name="ctl"),
            self._result(value=round(atl, 1), metric_name="atl"),
            self._result(value=round(tsb, 1), metric_name="tsb"),
            self._result(value=round(ramp_rate, 2), metric_name="ramp_rate"),
        ]

    def _get_daily_loads(self, ctx: CalcContext, days: int) -> dict:
        target = datetime.strptime(ctx.scope_id, "%Y-%m-%d")
        start = (target - timedelta(days=days)).strftime("%Y-%m-%d")
        end = ctx.scope_id
        rows = ctx.conn.execute("""
            SELECT substr(a.start_time, 1, 10) as date, m.numeric_value
            FROM metric_store m
            JOIN v_canonical_activities a ON CAST(m.scope_id AS INTEGER) = a.id
            WHERE m.scope_type = 'activity'
            AND m.metric_name = 'trimp' AND m.is_primary = 1
            AND substr(a.start_time, 1, 10) BETWEEN ? AND ?
        """, [start, end]).fetchall()
        daily: dict = {}
        for date, val in rows:
            daily[date] = daily.get(date, 0) + (val or 0)
        return daily
