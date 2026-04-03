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
        """CalcContext.get_daily_load() API를 사용하여 날짜별 TRIMP 합산."""
        target = datetime.strptime(ctx.scope_id, "%Y-%m-%d")
        daily: dict = {}
        for i in range(days + 1):
            ds = (target - timedelta(days=days - i)).strftime("%Y-%m-%d")
            load = ctx.get_daily_load(ds)
            if load:
                daily[ds] = load
        return daily
