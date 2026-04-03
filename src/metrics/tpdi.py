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
    ranges = {"consistent": 5, "moderate": 10, "large": 20}
    higher_is_better = False
    format_type = "number"
    decimal_places = 1

    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        target = ctx.scope_id
        td = date.fromisoformat(target)
        start = (td - timedelta(weeks=8)).isoformat()

        # 실외 FEARP
        outdoor_rows = ctx.conn.execute(
            "SELECT ms.numeric_value FROM metric_store ms "
            "JOIN activity_summaries a ON CAST(ms.scope_id AS INTEGER) = a.id "
            "WHERE ms.metric_name='fearp' AND ms.scope_type='activity' "
            "AND ms.numeric_value IS NOT NULL "
            "AND a.activity_type IN ('running', 'trail_running') "
            "AND DATE(a.start_time) BETWEEN ? AND ?",
            (start, target),
        ).fetchall()

        # 실내 FEARP
        indoor_rows = ctx.conn.execute(
            "SELECT ms.numeric_value FROM metric_store ms "
            "JOIN activity_summaries a ON CAST(ms.scope_id AS INTEGER) = a.id "
            "WHERE ms.metric_name='fearp' AND ms.scope_type='activity' "
            "AND ms.numeric_value IS NOT NULL "
            "AND a.activity_type = 'treadmill' "
            "AND DATE(a.start_time) BETWEEN ? AND ?",
            (start, target),
        ).fetchall()

        if not outdoor_rows or not indoor_rows:
            return []

        outdoor_avg = sum(r[0] for r in outdoor_rows) / len(outdoor_rows)
        indoor_avg = sum(r[0] for r in indoor_rows) / len(indoor_rows)

        if outdoor_avg <= 0:
            return []

        tpdi = round((outdoor_avg - indoor_avg) / outdoor_avg * 100, 1)

        return [self._result(
            value=tpdi,
            json_val={
                "outdoor_avg": round(outdoor_avg, 1),
                "indoor_avg": round(indoor_avg, 1),
                "outdoor_count": len(outdoor_rows),
                "indoor_count": len(indoor_rows),
            },
        )]
