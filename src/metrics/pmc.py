"""PMC (ATL/CTL/TSB/Ramp Rate) Calculator — 설계서 4-3 기준.

ATL = 7일, CTL = 42일 지수 가중 평균, TSB = CTL - ATL.
원문(v0.2/.ai/metrics.md) 재귀식 `CTL(n) = CTL(n-1) + (TRIMP - CTL(n-1)) / 42` → α = 1/τ
(DECISIONS [P7-UX-REVIEW-0928] D1). v1은 α = 2/(N+1)(실효 τ ≈ 21/4일)로 약 2배 빨리 반응했다.

재귀는 창 시작을 0으로 두므로 창이 짧으면 CTL이 과소 산출된다 — 6τ(252일) 창을 써서
초기값 영향을 e^-6 ≈ 0.25% 이하로 만든다(날짜별 독립 계산이라 재계산 순서와 무관).

달력 "오늘"은 아직 끝나지 않은 날이라 하루 전체를 휴식으로 가정하지 않는다 —
오늘까지 실제 발생한 부하는 전부 반영하되, 휴식에 의한 감쇠(1-α)는 하루 중 경과한
비율만큼만 적용한다(자정 직후 ≈ 어제 값, 하루가 끝나면 기존 일별 EMA와 동일).
"""
from __future__ import annotations

from datetime import datetime, timedelta

from src.metrics.base import CalcContext, CalcResult, MetricCalculator

ATL_DAYS = 7
CTL_DAYS = 42
# 부하 조회가 필요한 과거 일수 — engine의 daily load prefetch도 이 값을 쓴다.
LOAD_LOOKBACK_DAYS = 6 * CTL_DAYS


def elapsed_day_fraction(date_str: str, now: datetime | None = None) -> float:
    """date_str이 서버 로컬 "오늘"이면 하루 중 경과 비율(0~1), 과거 날짜는 1.0."""
    now = now or datetime.now()
    if date_str != now.strftime("%Y-%m-%d"):
        return 1.0
    seconds = now.hour * 3600 + now.minute * 60 + now.second
    return min(1.0, max(0.0, seconds / 86400))


def ewma_loads(daily_loads: dict, target: datetime, window_days: int,
               atl_alpha: float, ctl_alpha: float) -> tuple[float, float, float | None]:
    """target까지 창 window_days 동안 부하 EWMA. (atl, ctl, 전날 ctl) 반환."""
    atl = ctl = 0.0
    prev_ctl = None
    current = target - timedelta(days=window_days)
    while current <= target:
        ds = current.strftime("%Y-%m-%d")
        load = daily_loads.get(ds, 0)
        frac = elapsed_day_fraction(ds) if current == target else 1.0
        atl = atl * (1 - atl_alpha * frac) + load * atl_alpha
        prev_ctl = ctl
        ctl = ctl * (1 - ctl_alpha * frac) + load * ctl_alpha
        current += timedelta(days=1)
    return atl, ctl, prev_ctl


def get_daily_loads(ctx: CalcContext, days: int) -> dict:
    """CalcContext.get_daily_load() API로 날짜별 TRIMP 합산(0은 생략)."""
    target = datetime.strptime(ctx.scope_id, "%Y-%m-%d")
    daily: dict = {}
    for i in range(days + 1):
        ds = (target - timedelta(days=days - i)).strftime("%Y-%m-%d")
        load = ctx.get_daily_load(ds)
        if load:
            daily[ds] = load
    return daily


class PMCCalculator(MetricCalculator):
    name = "ctl"
    provider = "runpulse:formula_v1"
    version = "2.0"
    scope_type = "daily"
    category = "load"
    display_name = "PMC (ATL/CTL/TSB)"
    description = "Performance Management Chart. 42일 만성부하(CTL), 7일 급성부하(ATL), 훈련균형(TSB)."
    unit = "AU"
    higher_is_better = None
    requires = ["trimp"]
    produces = ["ctl", "atl", "tsb", "ramp_rate"]

    ATL_DAYS = ATL_DAYS
    CTL_DAYS = CTL_DAYS

    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        daily_loads = get_daily_loads(ctx, days=LOAD_LOOKBACK_DAYS)
        if not daily_loads:
            return []

        target = datetime.strptime(ctx.scope_id, "%Y-%m-%d")
        atl, ctl, prev_ctl = ewma_loads(
            daily_loads, target, LOAD_LOOKBACK_DAYS,
            atl_alpha=1.0 / self.ATL_DAYS, ctl_alpha=1.0 / self.CTL_DAYS,
        )
        tsb = ctl - atl
        ramp_rate = ctl - prev_ctl if prev_ctl is not None else 0

        return [
            self._result(value=round(ctl, 1), metric_name="ctl"),
            self._result(value=round(atl, 1), metric_name="atl"),
            self._result(value=round(tsb, 1), metric_name="tsb"),
            self._result(value=round(ramp_rate, 2), metric_name="ramp_rate",
                         parent_metric_name="ctl"),
        ]
