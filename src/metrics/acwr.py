"""ACWR Calculator — 설계서 4-3 기준. P7-PRED-89: 만성 부하가 형성되기 전(CTL < 10 또는 28일 전 CTL 없음)엔
산출하지 않는다("데이터 수집 중") — 이전엔 5.0으로 잘라 저장해 공백기 복귀일이 "위험"으로 보였다.

ACWR = ATL / CTL. 최적 범위: 0.8~1.3.
"""
from __future__ import annotations

from src.metrics.base import CalcContext, CalcResult, MetricCalculator


MIN_CTL = 10.0          # (c) 만성 부하 하한(TRIMP/일). 이 러너 CTL 중앙 ~50
HISTORY_DAYS = 28      # (a) EWMA 42일 상수에서 28일이면 정상상태의 약 49%


class ACWRCalculator(MetricCalculator):
    name = "acwr"
    provider = "runpulse:formula_v1"
    version = "1.0"
    scope_type = "daily"
    category = "load"
    display_name = "ACWR"
    description = "급성:만성 부하 비율. 최적 범위 0.8~1.3."
    unit = ""
    ranges = {"low": [0, 0.8], "optimal": [0.8, 1.3], "caution": [1.3, 1.5], "danger": [1.5, 5]}
    higher_is_better = None
    decimal_places = 2
    display_name = "ACWR"
    description = "급성:만성 부하 비율. 최적 범위 0.8~1.3."
    unit = ""
    ranges = {"low": [0, 0.8], "optimal": [0.8, 1.3], "caution": [1.3, 1.5], "danger": [1.5, 5]}
    higher_is_better = None
    decimal_places = 2
    requires = ["ctl", "atl"]

    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        atl = ctx.get_metric("atl", provider="runpulse:formula_v1")
        ctl = ctx.get_metric("ctl", provider="runpulse:formula_v1")
        if atl is None or ctl is None or ctl < MIN_CTL or not has_history(ctx):
            return []
        return [self._result(value=round(atl / ctl, 2))]


def has_history(ctx: CalcContext) -> bool:
    """28일 전에도 CTL 이 있었는가(만성 부하 형성 여부). DB 없는 컨텍스트(목)는 판단 불가 → True."""
    if getattr(ctx, "conn", None) is None:
        return True
    from datetime import date, timedelta
    d = (date.fromisoformat(ctx.scope_id) - timedelta(days=HISTORY_DAYS)).isoformat()
    return ctx.get_latest_daily_metric("ctl", d, provider="runpulse:formula_v1") is not None
