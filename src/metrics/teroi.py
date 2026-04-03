"""TEROI (Training Effect Return On Investment) — 훈련 효과 투자 수익률.

공식: TEROI = (CTL_end - CTL_start) / total_trimp × 1000
기간: 최근 28일. TRIMP 대비 CTL 증가 효율.

v0.3 포팅: _v02_backup/teroi.py → MetricCalculator 형식
"""
from __future__ import annotations

from datetime import date, timedelta
from src.metrics.base import MetricCalculator, CalcResult, CalcContext


class TEROICalculator(MetricCalculator):
    name = "teroi"
    provider = "runpulse:formula_v1"
    version = "1.0"
    scope_type = "daily"
    category = "rp_trend"
    requires = ["ctl", "trimp"]
    produces = ["teroi"]

    display_name = "TEROI (훈련 효과 ROI)"
    description = "TRIMP 투입 대비 CTL 증가율. 높을수록 효율적 훈련."
    unit = ""
    ranges = {"negative": [-100, 0], "low": [0, 5], "good": [5, 15], "excellent": [15, 100]}
    higher_is_better = True
    format_type = "number"
    decimal_places = 2

    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        target = ctx.scope_id
        td = date.fromisoformat(target)
        start = (td - timedelta(days=28)).isoformat()

        # CTL 시작/끝
        ctl_end = ctx.get_metric("ctl", provider="runpulse:formula_v1")
        if ctl_end is None:
            return []
        ctl_end = float(ctl_end)

        # CalcContext API 활용 (보강 #1)
        series = ctx.get_daily_metric_series("ctl", days=28, provider="runpulse:formula_v1")
        ctl_start = series[0][1] if series else 0.0

        # 28일간 총 TRIMP
        trimp_series = ctx.get_activity_metric_series("trimp", days=28)
        total_trimp = sum(d["numeric"] for d in trimp_series) if trimp_series else 0.0

        if total_trimp <= 0:
            return []

        ctl_delta = ctl_end - ctl_start
        teroi = round(ctl_delta / total_trimp * 1000, 2)

        return [self._result(
            value=teroi,
            json_val={
                "ctl_start": round(ctl_start, 1),
                "ctl_end": round(ctl_end, 1),
                "total_trimp": round(total_trimp, 1),
            },
        
            confidence=1.0,
        )]
