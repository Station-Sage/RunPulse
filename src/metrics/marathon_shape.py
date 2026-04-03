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
    ranges = {"insufficient": 30, "base": 50, "building": 70, "ready": 85, "peak": 95}
    higher_is_better = True
    format_type = "number"
    decimal_places = 1

    def compute(self, ctx: CalcContext) -> list[CalcResult]:
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

        # 최근 4주 주간 평균 거리
        weeks = 4
        start = (td - timedelta(weeks=weeks)).isoformat()
        dist_row = ctx.conn.execute(
            "SELECT SUM(distance_m) FROM activity_summaries "
            "WHERE activity_type='running' "
            "AND DATE(start_time) BETWEEN ? AND ?",
            (start, target),
        ).fetchone()
        total_km = float(dist_row[0]) / 1000.0 if dist_row and dist_row[0] else 0.0
        weekly_avg = total_km / weeks

        # 최근 12주 최장 거리 런
        long_start = (td - timedelta(weeks=12)).isoformat()
        long_row = ctx.conn.execute(
            "SELECT MAX(distance_m) FROM activity_summaries "
            "WHERE activity_type='running' "
            "AND DATE(start_time) BETWEEN ? AND ?",
            (long_start, target),
        ).fetchone()
        longest_km = float(long_row[0]) / 1000.0 if long_row and long_row[0] else 0.0

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
