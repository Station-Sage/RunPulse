"""REC (Running Efficiency Composite) — 통합 러닝 효율성 지수.

최근 7일 EF/Decoupling 평균으로 0~100 정규화.

공식:
    dec_factor = max(0.5, 1.0 - decoupling/100)
    raw = ef * dec_factor * form_factor
    REC = clamp((raw - 0.8) / 1.2 * 100, 0, 100)

v0.3 포팅: _v02_backup/rec.py → MetricCalculator 형식
"""
from __future__ import annotations

from datetime import date, timedelta
from src.metrics.base import MetricCalculator, CalcResult, CalcContext


class RECCalculator(MetricCalculator):
    name = "rec"
    provider = "runpulse:formula_v1"
    version = "1.0"
    scope_type = "daily"
    category = "rp_performance"
    requires = ["efficiency_factor_rp", "aerobic_decoupling_rp"]
    produces = ["rec"]

    display_name = "REC (러닝 효율성)"
    description = "EF와 Decoupling 기반 통합 러닝 효율성 (0~100)"
    unit = ""
    ranges = {"poor": 30, "fair": 50, "good": 70, "excellent": 85}
    higher_is_better = True
    format_type = "number"
    decimal_places = 1

    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        target = ctx.scope_id
        td = date.fromisoformat(target)
        start = (td - timedelta(days=7)).isoformat()

        # 최근 7일 EF
        ef_rows = ctx.conn.execute(
            "SELECT ms.numeric_value FROM metric_store ms "
            "JOIN activity_summaries a ON CAST(ms.scope_id AS INTEGER) = a.id "
            "WHERE ms.metric_name='efficiency_factor_rp' AND ms.scope_type='activity' "
            "AND ms.numeric_value IS NOT NULL "
            "AND DATE(a.start_time) BETWEEN ? AND ?",
            (start, target),
        ).fetchall()
        if not ef_rows:
            return []
        ef_avg = sum(r[0] for r in ef_rows) / len(ef_rows)

        # 최근 7일 Decoupling
        dec_rows = ctx.conn.execute(
            "SELECT ms.numeric_value FROM metric_store ms "
            "JOIN activity_summaries a ON CAST(ms.scope_id AS INTEGER) = a.id "
            "WHERE ms.metric_name='aerobic_decoupling_rp' AND ms.scope_type='activity' "
            "AND ms.numeric_value IS NOT NULL "
            "AND DATE(a.start_time) BETWEEN ? AND ?",
            (start, target),
        ).fetchall()
        dec_avg = sum(r[0] for r in dec_rows) / len(dec_rows) if dec_rows else 5.0

        dec_factor = max(0.5, 1.0 - dec_avg / 100)
        raw = ef_avg * dec_factor
        rec = min(100, max(0, (raw - 0.8) / 1.2 * 100))

        return [self._result(
            value=round(rec, 1),
            json_val={
                "ef_avg": round(ef_avg, 4),
                "dec_avg": round(dec_avg, 1),
                "ef_count": len(ef_rows),
            },
        )]
