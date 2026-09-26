"""REC (Running Efficiency Composite) — 통합 러닝 효율성 지수.

최근 7일 EF(디커플링 보정)가 본인 최근 180일 분포에서 어디쯤인지(백분위, 0~100).

공식 (v2, P7-PRED-82):
    raw_i = ef_i * max(0.5, 1 - decoupling_i/100)   (활동별, 디커플링 없으면 5%)
    current = 최근 7일 raw 평균
    REC = 100 * (#{raw_j < current} + 0.5 * #{raw_j == current}) / n   (j: 최근 180일, n >= 5)
v1 은 EF 를 m/min/bpm(≈1.2) 로 가정했으나 저장값은 m/s/bpm×1000(≈19) 이라 958일 모두 100 으로 포화됐다.

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
    category = "efficiency"
    requires = ["efficiency_factor_rp", "aerobic_decoupling_rp"]
    produces = ["rec"]

    display_name = "REC (러닝 효율성)"
    description = "EF와 Decoupling 기반 통합 러닝 효율성 (0~100)"
    unit = ""
    ranges = {"poor": [0, 30], "fair": [30, 50], "good": [50, 70], "excellent": [70, 100]}
    higher_is_better = True
    format_type = "number"
    decimal_places = 1

    MIN_REF = 5

    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        ef = ctx.get_activity_metric_series("efficiency_factor_rp", days=180, canonical_only=True, primary_only=True)
        dec = {d["activity_id"]: d["numeric"] for d in
               ctx.get_activity_metric_series("aerobic_decoupling_rp", days=180, canonical_only=True, primary_only=True)}
        if len(ef) < self.MIN_REF:
            return []
        raws = [(d["date"], d["numeric"] * max(0.5, 1.0 - dec.get(d["activity_id"], 5.0) / 100)) for d in ef]
        cut = (date.fromisoformat(ctx.scope_id) - timedelta(days=7)).isoformat()
        recent = [r for dt, r in raws if dt > cut]
        if not recent:
            return []
        cur = sum(recent) / len(recent)
        vals = [r for _, r in raws]
        rank = (sum(1 for v in vals if v < cur) + 0.5 * sum(1 for v in vals if v == cur)) / len(vals)
        return [self._result(value=round(100 * rank, 1),
                             json_val={"current_raw": round(cur, 3), "n_ref": len(vals), "n_recent": len(recent)},
                             confidence=min(1.0, len(vals) / 30))]
