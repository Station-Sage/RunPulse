"""TIDS (Training Intensity Distribution Score) — 설계서 4-4 기준.

8주간 훈련 강도 분포 분석 (polarized/threshold/pyramidal).
"""
from __future__ import annotations

from src.metrics.base import CalcContext, CalcResult, MetricCalculator


class TIDSCalculator(MetricCalculator):
    name = "tids"
    provider = "runpulse:formula_v1"
    version = "1.0"
    scope_type = "daily"
    category = "rp_training"

    display_name = "강도 분포 (TIDS)"
    description = "8주간 훈련 강도 분포. polarized/threshold/pyramidal/mixed."
    format_type = "json"
    requires = ["workout_type"]

    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        activities = ctx.get_activities_in_range(days=56, activity_type="running")
        if len(activities) < 5:
            return []

        types = {"easy": 0, "recovery": 0, "tempo": 0, "threshold": 0,
                 "interval": 0, "long_run": 0, "race": 0, "unknown": 0}

        for act in activities:
            # workout_type은 text_value에 저장됨
            row = ctx.conn.execute(
                "SELECT text_value FROM metric_store "
                "WHERE scope_type='activity' AND scope_id=? "
                "AND metric_name='workout_type' AND is_primary=1",
                [str(act["id"])]
            ).fetchone()
            wt_type = row[0] if row and row[0] else "unknown"
            types[wt_type] = types.get(wt_type, 0) + 1

        total = sum(types.values()) or 1
        pcts = {k: round(v / total * 100, 1) for k, v in types.items()}

        low = pcts.get("easy", 0) + pcts.get("recovery", 0) + pcts.get("long_run", 0)
        mid = pcts.get("tempo", 0) + pcts.get("threshold", 0)
        high = pcts.get("interval", 0) + pcts.get("race", 0)

        if low >= 70 and high >= 15:
            pattern = "polarized"
        elif mid >= 40:
            pattern = "threshold"
        elif low >= 60 and mid >= 20:
            pattern = "pyramidal"
        else:
            pattern = "mixed"

        return [self._result(
            json_val={"distribution": pcts, "pattern": pattern,
                      "low_pct": low, "mid_pct": mid, "high_pct": high},
            text=pattern,
        )]
