"""GAP (Grade Adjusted Pace) Calculator — Minetti (2002) 에너지 비용 모델.

v2(UX 리뷰 20 F-DATA-05, DECISIONS D11):
- 경사: 스트림 `grade_pct`가 있으면 그 값, 없으면 고도에서 거리 30m 이상 창으로 계산(GPS 고도 노이즈 억제).
- 보정 방향: 등가 평지 거리 = 실제 거리 × (경사 비용 / 평지 비용). v1은 나눠서 오르막 보정이 반대였다.
- 정지 구간 제외(stream_utils.moving_segments). 경사·고도 데이터가 없으면 결과를 내지 않는다.
"""
from __future__ import annotations

from src.metrics.base import CalcContext, CalcResult, MetricCalculator
from src.metrics.stream_utils import moving_segments

GRADE_WINDOW_M = 30.0
MAX_GRADE = 0.45          # Minetti 측정 범위(±45%)
FLAT_COST = 3.6


class GAPCalculator(MetricCalculator):
    name = "gap_rp"
    provider = "runpulse:formula_v1"
    version = "minetti_2002_v2"
    scope_type = "activity"
    category = "capacity"
    display_name = "GAP (경사 보정 페이스)"
    description = "Minetti 모델로 경사를 보정한 평지 환산 페이스."
    unit = "sec/km"
    format_type = "pace"
    higher_is_better = False
    needs_streams = True
    requires = []

    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        streams = ctx.get_group_streams()
        if not streams or len(streams) < 60:
            return []
        grades = stream_grades(streams)
        if grades is None:
            return []
        act = ctx.activity or {}
        segs = moving_segments(streams, act.get("elapsed_time_sec") or act.get("duration_sec"))

        adj_dist = total_time = 0.0
        for seg in segs:
            g = grades[seg["i"]]
            if g is None:
                continue
            adj_dist += seg["speed"] * seg["dt"] * effort_factor(g)
            total_time += seg["dt"]
        if total_time <= 0 or adj_dist <= 0:
            return []
        return [self._result(value=round(total_time / adj_dist * 1000.0, 1))]


def effort_factor(grade: float) -> float:
    """경사(비율) → 평지 대비 에너지 비용 배수(Minetti 2002)."""
    g = max(-MAX_GRADE, min(MAX_GRADE, grade))
    cost = 155.4 * g**5 - 30.4 * g**4 - 43.3 * g**3 + 46.3 * g**2 + 19.5 * g + FLAT_COST
    return max(cost, 0.5) / FLAT_COST


def stream_grades(streams: list[dict]) -> list[float | None] | None:
    """샘플별 경사(비율). grade_pct가 채워져 있으면 사용, 아니면 고도·거리로 계산. 둘 다 없으면 None."""
    if any(s.get("grade_pct") is not None for s in streams):
        return [(s["grade_pct"] / 100.0) if s.get("grade_pct") is not None else None for s in streams]
    valid = [i for i, s in enumerate(streams) if s.get("altitude_m") is not None and s.get("distance_m") is not None]
    if len(valid) < len(streams) * 0.5:
        return None
    alt = [streams[i]["altitude_m"] for i in valid]
    dist = [streams[i]["distance_m"] for i in valid]
    out: list[float | None] = [None] * len(streams)
    j = 0
    for n, i in enumerate(valid):
        # j = 현재 샘플보다 30m 이상 뒤에 있는 가장 가까운 샘플
        while j + 1 < n and dist[n] - dist[j + 1] >= GRADE_WINDOW_M:
            j += 1
        span = dist[n] - dist[j]
        if span >= GRADE_WINDOW_M:
            out[i] = (alt[n] - alt[j]) / span
    first = next((g for g in out if g is not None), None)
    if first is None:
        return None
    for i in range(len(out)):          # 창이 아직 안 찬 앞부분은 첫 계산값으로 채움
        if out[i] is not None:
            break
        out[i] = first
    return out
