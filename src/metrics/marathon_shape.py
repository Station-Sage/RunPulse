"""Marathon Shape — 마라톤 훈련 완성도.

공식 (Runalyze 방식):
    weekly_shape = min(1.0, weekly_km / target_weekly_km)
    long_shape   = min(1.0, longest_km / target_long_km)
    shape_pct    = (weekly_shape × 2/3 + long_shape × 1/3) × 100

v0.3 포팅: _v02_backup/marathon_shape.py → MetricCalculator 형식
"""
from __future__ import annotations

from datetime import date, timedelta, datetime
from src.metrics.base import MetricCalculator, CalcResult, CalcContext


class MarathonShapeCalculator(MetricCalculator):
    name = "marathon_shape"
    provider = "runpulse:formula_v1"
    version = "1.0"
    scope_type = "daily"
    category = "rp_performance"
    requires = ["runpulse_vdot"]
    produces = ["marathon_shape"]

    display_name = "Marathon Shape"
    description = "마라톤 훈련 완성도 (%). 주간볼륨+장거리런 기반."
    unit = "%"
    ranges = {"insufficient": [0, 30], "base": [30, 50], "building": [50, 70], "ready": [70, 85], "peak": [85, 100]}
    higher_is_better = True
    format_type = "number"
    decimal_places = 1

    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        # NOTE: raw SQL 사용 — CalcContext API가 activity_type별 metric JOIN을 미지원
        # VDOT (vdot_adj 우선, 없으면 runpulse_vdot)
        vdot_val = ctx.get_metric("vdot_adj", provider="runpulse:formula_v1")
        if vdot_val is None:
            vdot_val = ctx.get_metric("runpulse_vdot", provider="runpulse:formula_v1")
        if vdot_val is None:
            return []
        vdot = float(vdot_val)

        target = ctx.scope_id
        td = date.fromisoformat(target)

        # 목표 볼륨 (Daniels 기준)
        from src.utils.daniels_table import get_race_volume_targets
        race_km = 42.195
        targets = get_race_volume_targets(vdot, race_km)
        weekly_target = targets.get("weekly_target", 70)
        long_max = targets.get("long_max", 32)

        # 최근 4주 주간 평균 거리 — CalcContext API
        weeks = 4
        activities_4w = ctx.get_activities_in_range(days=weeks * 7, activity_type="running")
        distances_4w = [a["distance_m"] for a in activities_4w if a.get("distance_m")]
        total_km = sum(distances_4w) / 1000.0
        weekly_avg = total_km / weeks

        # 최근 12주 최장 거리 런
        activities_12w = ctx.get_activities_in_range(days=84, activity_type="running")
        distances_12w = [a["distance_m"] for a in activities_12w if a.get("distance_m")]
        longest_km = max(distances_12w) / 1000.0 if distances_12w else 0.0

        # Shape 계산
        weekly_shape = min(1.0, weekly_avg / weekly_target) if weekly_target > 0 else 0.0
        long_shape = min(1.0, longest_km / long_max) if long_max > 0 else 0.0
        shape_pct = round((weekly_shape * 2 / 3 + long_shape * 1 / 3) * 100, 1)

        label = self._label(shape_pct)

        return [self._result(
            value=shape_pct,
            json_val={
                "label": label,
                "weekly_km_avg": round(weekly_avg, 1),
                "longest_run_km": round(longest_km, 1),
                "vdot": round(vdot, 1),
                "target_weekly_km": round(weekly_target, 1),
                "target_long_km": round(long_max, 1),
            },
        
            confidence=1.0,
        )]

    @staticmethod
    def _label(shape_pct: float) -> str:
        if shape_pct < 30:
            return "insufficient"
        if shape_pct < 50:
            return "base"
        if shape_pct < 70:
            return "building"
        if shape_pct < 85:
            return "ready"
        return "peak"
