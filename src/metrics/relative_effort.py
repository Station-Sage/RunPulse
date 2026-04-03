"""Relative Effort (Strava 방식) — 심박존 기반 노력도 점수.

공식: zone_coefficients = [0.5, 1.0, 2.0, 3.5, 5.5]
      RE = sum(time_in_zone_sec[i] / 60 * coeff[i])

v0.3 포팅: _v02_backup/relative_effort.py → MetricCalculator 형식
"""
from __future__ import annotations

from src.metrics.base import MetricCalculator, CalcResult, CalcContext

_ZONE_COEFFICIENTS = [0.5, 1.0, 2.0, 3.5, 5.5]


class RelativeEffortCalculator(MetricCalculator):
    name = "relative_effort"
    provider = "runpulse:formula_v1"
    version = "1.0"
    scope_type = "activity"
    category = "rp_load"
    requires = []  # activity_summaries.avg_hr 직접 조회 (소스 컬럼)
    produces = ["relative_effort"]

    display_name = "Relative Effort"
    description = "심박존 기반 노력도 점수 (Strava 방식)"
    unit = "AU"
    ranges = {"low": [0, 50], "moderate": [50, 100], "high": [100, 200], "very_high": [200, 999]}
    higher_is_better = None
    format_type = "number"
    decimal_places = 1

    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        act = ctx.activity
        if not act:
            return []

        # 1차: metric_store에서 HR zone 시간 데이터
        zone_secs = []
        for z in range(1, 6):
            for pattern in [f"hr_zone_{z}_sec", f"heartrate_zone_{z}_sec"]:
                val = ctx.get_metric(pattern)
                if val is not None:
                    zone_secs.append(float(val))
                    break
            else:
                zone_secs.append(0.0)

        # 2차: avg_hr 기반 근사 (zone 데이터 없을 때)
        if sum(zone_secs) <= 0:
            avg_hr = act.get("avg_hr")
            max_hr = act.get("max_hr")
            duration = act.get("moving_time_sec") or act.get("elapsed_time_sec")
            if not avg_hr or not max_hr or not duration or max_hr <= 0:
                return []
            ratio = float(avg_hr) / float(max_hr)
            zone_secs = [0.0] * 5
            dur = float(duration)
            if ratio < 0.60:
                zone_secs[0] = dur
            elif ratio < 0.70:
                zone_secs[1] = dur
            elif ratio < 0.80:
                zone_secs[2] = dur
            elif ratio < 0.90:
                zone_secs[3] = dur
            else:
                zone_secs[4] = dur

        if sum(zone_secs) <= 0:
            return []

        re = sum(sec / 60.0 * coeff
                 for sec, coeff in zip(zone_secs, _ZONE_COEFFICIENTS))

        conf = 0.9 if sum(1 for s in zone_secs if s > 0) > 1 else 0.6
        return [self._result(value=round(re, 1), confidence=conf)]
