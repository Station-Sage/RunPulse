"""Aerobic Decoupling Calculator — 설계서 4-2 기준.

Decoupling = (EF_first_half - EF_second_half) / EF_first_half × 100
EF = avg_speed / avg_hr
< 5% = good aerobic fitness
"""
from __future__ import annotations

from src.metrics.base import CalcContext, CalcResult, MetricCalculator
from src.metrics.stream_utils import moving_segments


class AerobicDecouplingCalculator(MetricCalculator):
    name = "aerobic_decoupling_rp"
    provider = "runpulse:formula_v1"
    version = "2.0"
    scope_type = "activity"
    category = "efficiency"
    display_name = "유산소 분리"
    description = "후반부 효율 저하율. <5% = 좋은 유산소 체력."
    unit = "%"
    ranges = {"excellent": [-5, 5], "good": [5, 10], "fair": [10, 15], "poor": [15, 100]}
    higher_is_better = False
    decimal_places = 2
    display_name = "유산소 분리"
    description = "후반부 효율 저하율. <5% = 좋은 유산소 체력."
    unit = "%"
    ranges = {"excellent": [-5, 5], "good": [5, 10], "fair": [10, 15], "poor": [15, 100]}
    higher_is_better = False
    decimal_places = 2
    needs_streams = True
    requires = []

    MINIMUM_DURATION_SEC = 1200  # 20분

    WARMUP_SEC = 600  # Friel 관행: 첫 10분 제외

    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        """Friel 방식: 워밍업 10분 제외, 정지 제외한 **이동 시간** 기준 전·후반 EF(속도/심박) 비교."""
        act = ctx.activity
        duration = act.get("moving_time_sec") or act.get("duration_sec")
        if not duration or duration < self.MINIMUM_DURATION_SEC:
            return []

        streams = ctx.get_streams()
        if not streams or len(streams) < 120:
            return []

        segs = [s for s in moving_segments(streams, act.get("elapsed_time_sec") or duration) if s["hr"]]
        t, body = 0.0, []
        for seg in segs:
            t += seg["dt"]
            if t > self.WARMUP_SEC:
                body.append(seg)
        total = sum(s["dt"] for s in body)
        if total < self.MINIMUM_DURATION_SEC - self.WARMUP_SEC:
            return []

        half, acc, first, second = total / 2, 0.0, [], []
        for seg in body:
            (first if acc < half else second).append(seg)
            acc += seg["dt"]
        ef_first, ef_second = _ef(first), _ef(second)
        if not ef_first or ef_second is None:
            return []
        decoupling = (ef_first - ef_second) / ef_first * 100
        return [self._result(value=round(decoupling, 2))]


def _ef(segs: list[dict]) -> float | None:
    """시간 가중 평균 속도 / 평균 심박."""
    dt = sum(s["dt"] for s in segs)
    if dt <= 0:
        return None
    speed = sum(s["speed"] * s["dt"] for s in segs) / dt
    hr = sum(s["hr"] * s["dt"] for s in segs) / dt
    return speed / hr if hr > 0 else None
