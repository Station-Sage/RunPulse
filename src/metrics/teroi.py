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
    category = "rp_performance"
    requires = ["ctl", "trimp"]
    produces = ["teroi"]

    display_name = "TEROI (훈련 효과 ROI)"
    description = "TRIMP 투입 대비 CTL 증가율. 높을수록 효율적 훈련."
    unit = ""
    ranges = {"negative": 0, "low": 5, "good": 15, "excellent": 30}
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

        row = ctx.conn.execute(
            "SELECT numeric_value FROM metric_store "
            "WHERE metric_name='ctl' AND scope_type='daily' "
            "AND scope_id=? AND numeric_value IS NOT NULL "
            "ORDER BY scope_id DESC LIMIT 1",
            (start,),
        ).fetchone()
        ctl_start = float(row[0]) if row else 0.0

        # 28일간 총 TRIMP
        rows = ctx.conn.execute(
            "SELECT SUM(ms.numeric_value) FROM metric_store ms "
            "JOIN activity_summaries a ON CAST(ms.scope_id AS INTEGER) = a.id "
            "WHERE ms.metric_name='trimp' AND ms.scope_type='activity' "
            "AND ms.numeric_value IS NOT NULL "
            "AND DATE(a.start_time) BETWEEN ? AND ?",
            (start, target),
        ).fetchone()
        total_trimp = float(rows[0]) if rows and rows[0] else 0.0

        if total_trimp <= 0:
            return []

        ctl_delta = ctl_end - ctl_start
        teroi = round(ctl_delta / total_trimp * 1000, 2)

        return [self._result(
            value=teroi,
            json_value={
                "ctl_start": round(ctl_start, 1),
                "ctl_end": round(ctl_end, 1),
                "total_trimp": round(total_trimp, 1),
            },
        )]
