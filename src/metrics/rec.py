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
    category = "rp_efficiency"
    requires = ["efficiency_factor_rp", "aerobic_decoupling_rp"]
    produces = ["rec"]

    display_name = "REC (러닝 효율성)"
    description = "EF와 Decoupling 기반 통합 러닝 효율성 (0~100)"
    unit = ""
    ranges = {"poor": [0, 30], "fair": [30, 50], "good": [50, 70], "excellent": [70, 100]}
    higher_is_better = True
    format_type = "number"
    decimal_places = 1

    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        # NOTE: raw SQL 사용 — CalcContext API가 activity_type별 metric JOIN을 미지원
        target = ctx.scope_id
        td = date.fromisoformat(target)
        start = (td - timedelta(days=7)).isoformat()

        # 최근 7일 EF — CalcContext API
        ef_data = ctx.get_activity_metric_series("efficiency_factor_rp", days=7)
        if not ef_data:
            return []
        ef_avg = sum(d["numeric"] for d in ef_data) / len(ef_data)

        # 최근 7일 Decoupling
        dec_data = ctx.get_activity_metric_series("aerobic_decoupling_rp", days=7)
        dec_avg = sum(d["numeric"] for d in dec_data) / len(dec_data) if dec_data else 5.0

        dec_factor = max(0.5, 1.0 - dec_avg / 100)
        raw = ef_avg * dec_factor
        rec = min(100, max(0, (raw - 0.8) / 1.2 * 100))

        return [self._result(
            value=round(rec, 1),
            json_val={
                "ef_avg": round(ef_avg, 4),
                "dec_avg": round(dec_avg, 1),
                "ef_count": len(ef_data),
            },
        
            confidence=1.0,
        )]
