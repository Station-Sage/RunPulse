"""계획↔활동 매칭 선택 규칙(순수) — 같은 날 활동 중 계획에 맞는 하나를 고르고, 결과 라벨을 분류한다.

기존 결함: 같은 날 러닝이면 거리 차이와 무관하게 '완료'로 묶고, 다른 계획이 이미 가져간 활동도 다시 가져갔다.
  - 이미 다른 계획(Garmin 저장 워크아웃·Intervals 이벤트 등 명시 연결)이 가져간 활동은 제외한다.
  - 거리 비율이 [MIN_RATIO, MAX_RATIO] 밖이면 다른 세션으로 보고 매칭하지 않는다.
  - 완료(completed=1)는 거리 이행률 DONE_RATIO 이상일 때만. 그 미만은 연결·라벨만 남기고 미이행으로 둔다.
"""
from __future__ import annotations

MIN_RATIO, MAX_RATIO = 0.5, 1.6
DONE_RATIO = 0.75


def pick_activity(plan_dist: float | None, day_acts: list[tuple], claimed: set[int]) -> tuple | None:
    """day_acts 행 = (id, date, distance_km, ...). 거리 기준 가장 가까운 미점유·호환 활동 하나."""
    free = [a for a in day_acts if a[0] not in claimed]
    if not free:
        return None
    if not plan_dist:
        return free[0]
    ok = [a for a in free if a[2] and MIN_RATIO <= a[2] / plan_dist <= MAX_RATIO]
    return min(ok, key=lambda a: abs(a[2] - plan_dist)) if ok else None


def is_done(plan_dist: float | None, act_dist: float | None) -> bool:
    if not plan_dist or not act_dist:
        return True
    return act_dist / plan_dist >= DONE_RATIO


def classify_outcome(dist_ratio: float | None, pace_delta_pct: float | None) -> str:
    """거리 이행이 우선 — 짧게 뛰고 빨랐던 것은 '초과 달성'이 아니다."""
    if dist_ratio is None:
        return "modified"
    if dist_ratio < 0.50:
        return "skipped"
    if dist_ratio < 0.85:
        return "underperformed"
    if dist_ratio > 1.10 or (pace_delta_pct is not None and pace_delta_pct < -5.0):
        return "overperformed"
    if pace_delta_pct is not None and pace_delta_pct > 5.0:
        return "underperformed"
    return "on_target"
