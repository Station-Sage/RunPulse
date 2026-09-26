"""훈련 반응(일별) — 품질 세트 구간별 주간 시간·품질 세션 수·롱런 MP 거리·세트 VDOT 추세(P7-PRED-41, r4).

기기(HR) 없이 동작하고 PB 에 의존하지 않는다. 예측 중앙값에는 세트가 관측으로 직접 들어가므로(DARP) 이 메트릭은 설명용이다.
produces training_response: numeric = 최근 8주 주평균 품질 작업 분, json = 구간별 주간 값·이전 8주·세션 수·MP 거리·추세.
"""
from __future__ import annotations

from src.metrics.base import CalcContext, CalcResult, MetricCalculator
from src.metrics.prediction import response as rs
from src.metrics.prediction.daniels import time_for_vdot


class TrainingResponseCalculator(MetricCalculator):
    name = "training_response"
    provider = "runpulse:formula_v1"
    version = "2.0"
    scope_type = "daily"
    category = "load"
    display_name = "훈련 반응"
    description = "최근 8주 품질 세트(R/I/T/M) 주간 작업 시간과 이전 8주 비교, 품질 세션 수, 롱런 속 마라톤 페이스 구간, 세트 VDOT 추세."
    unit = "min/wk"
    format_type = "number"
    requires = ["race_pred_vdot"]
    produces = ["training_response"]

    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        day = ctx.scope_id
        runs = ctx.get_runs(16 * 7 + 90, with_laps=True, include_end=False)
        if not runs:
            return []
        weekly = rs.weekly_zone_minutes(runs, day)
        out = {"weekly_zone_min": weekly, **rs.summarize(weekly), "trend": rs.set_trend(runs, day)}
        vd = ctx.get_latest_daily_metric("race_pred_vdot", day, provider="runpulse:formula_v1")
        if vd:
            out["long_mp_km_8w"] = rs.long_mp_km(runs, day, 42195.0 / time_for_vdot(vd, 42195.0))
        return [self._result(value=out["quality_min_avg_8w"], json_val=out, confidence=0.7)]
