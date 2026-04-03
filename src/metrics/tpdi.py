"""TPDI (Trainer Physical Disparity Index) — 실내/실외 FEARP 격차 지수.

공식: TPDI = (outdoor_avg - indoor_avg) / outdoor_avg × 100
최근 8주간 실내/실외 FEARP 비교.

v0.3 포팅: _v02_backup/tpdi.py → MetricCalculator 형식
"""
from __future__ import annotations

from datetime import date, timedelta
from src.metrics.base import MetricCalculator, CalcResult, CalcContext


class TPDICalculator(MetricCalculator):
    name = "tpdi"
    provider = "runpulse:formula_v1"
    version = "1.0"
    scope_type = "daily"
    category = "rp_trend"
    requires = ["fearp"]
    produces = ["tpdi"]

    display_name = "TPDI (실내/실외 격차)"
    description = "실내 vs 실외 달리기 FEARP 격차. 0에 가까울수록 일관됨."
    unit = "%"
    ranges = {"consistent": [0, 5], "moderate": [5, 10], "large": [10, 100]}
    higher_is_better = False
    format_type = "number"
    decimal_places = 1

    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        # NOTE: raw SQL 사용 — CalcContext API가 activity_type별 metric JOIN을 미지원
        target = ctx.scope_id
        td = date.fromisoformat(target)
        start = (td - timedelta(weeks=8)).isoformat()

        # 실외/실내 FEARP — CalcContext API
        outdoor_data = ctx.get_activity_metric_series("fearp", days=56, activity_type="running")
        trail_data = ctx.get_activity_metric_series("fearp", days=56, activity_type="trail_running")
        outdoor_data = outdoor_data + trail_data
        indoor_data = ctx.get_activity_metric_series("fearp", days=56, activity_type="treadmill")

        if not outdoor_data or not indoor_data:
            return []

        outdoor_avg = sum(d["numeric"] for d in outdoor_data) / len(outdoor_data)
        indoor_avg = sum(d["numeric"] for d in indoor_data) / len(indoor_data)

        if outdoor_avg <= 0:
            return []

        tpdi = round((outdoor_avg - indoor_avg) / outdoor_avg * 100, 1)

        return [self._result(
            value=tpdi,
            json_val={
                "outdoor_avg": round(outdoor_avg, 1),
                "indoor_avg": round(indoor_avg, 1),
                "outdoor_count": len(outdoor_data),
                "indoor_count": len(indoor_data),
            },
        
            confidence=1.0,
        )]
