"""Relative Effort (Strava 방식) — 심박존 기반 노력도 점수.

공식: zone_coefficients = [0.5, 1.0, 2.0, 3.5, 5.5]
      RE = sum(time_in_zone_sec[i] / 60 * coeff[i])

v0.3 포팅: _v02_backup/relative_effort.py → MetricCalculator 형식
"""
from __future__ import annotations

from src.metrics.base import MetricCalculator, CalcResult, CalcContext
from src.metrics.stream_utils import athlete_max_hr, moving_segments

_ZONE_COEFFICIENTS = [0.5, 1.0, 2.0, 3.5, 5.5]


class RelativeEffortCalculator(MetricCalculator):
    name = "relative_effort"
    provider = "runpulse:formula_v1"
    version = "2.0"
    scope_type = "activity"
    category = "load"
    requires = []  # activity_summaries.avg_hr 직접 조회 (소스 컬럼)
    needs_streams = True
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

        conf = 0.9
        # 2차: 스트림 심박으로 존 체류 시간 적분(선수 최대심박 기준, 정지 제외)
        if sum(zone_secs) <= 0:
            zone_secs = self._zones_from_streams(ctx, act)
            conf = 0.85
        # 3차: 평균 심박 근사 — 분모는 **선수** 최대심박(활동 자신의 최대심박이면 이지런이 Z5가 된다)
        if sum(zone_secs) <= 0:
            avg_hr = act.get("avg_hr")
            duration = act.get("moving_time_sec") or act.get("duration_sec") or act.get("elapsed_time_sec")
            if not avg_hr or not duration:
                return []
            zone_secs = [0.0] * 5
            zone_secs[_zone_index(float(avg_hr) / athlete_max_hr(ctx))] = float(duration)
            conf = 0.6

        if sum(zone_secs) <= 0:
            return []

        re = sum(sec / 60.0 * coeff
                 for sec, coeff in zip(zone_secs, _ZONE_COEFFICIENTS))
        return [self._result(value=round(re, 1), confidence=conf)]

    def _zones_from_streams(self, ctx: CalcContext, act: dict) -> list[float]:
        streams = ctx.get_streams()
        if not streams:
            return [0.0] * 5
        max_hr = athlete_max_hr(ctx)
        total = act.get("elapsed_time_sec") or act.get("duration_sec")
        zones = [0.0] * 5
        for seg in moving_segments(streams, total):
            if seg["hr"]:
                zones[_zone_index(seg["hr"] / max_hr)] += seg["dt"]
        return zones


def _zone_index(ratio: float) -> int:
    """%HRmax → 존 인덱스(0~4): <60 / <70 / <80 / <90 / 그 이상."""
    for i, upper in enumerate((0.60, 0.70, 0.80, 0.90)):
        if ratio < upper:
            return i
    return 4
