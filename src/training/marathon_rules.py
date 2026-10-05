"""마라톤 페이스(MP) 규칙 R6(순수) — 처방 MP, 롱런 페이스, long_mp 비중, 테이퍼 MP 세션 (DESIGN-U16 §2.3).

페이스 단위는 초/km. DB를 읽지 않는다.
"""
from __future__ import annotations

MP_PROGRESS_SEC_PER_WEEK = 2.5
MP_MAX_GAIN_SEC = 12.0
LONG_PACE_FACTOR = 1.15
LONG_PACE_RANGE = (1.10, 1.20)
MP_SHARE = {"build": (0.20, 0.30), "peak": (0.40, 0.50)}
TAPER1_MP_KM = (10.0, 13.0)
RACE_WEEK_MP_KM = (3.0, 5.0)
RACE_WEEK_MIN_TOTAL_KM = 6.0


def prescribed_mp(mp_now: float | None, mp_goal: float | None, weeks_since_build: int) -> float | None:
    """처방 MP = max(목표 MP, 현재 MP − 2.5초×경과 주), 현재 MP보다 12초 넘게 빠르지 않게. 목표 없음이면 현재 MP."""
    if mp_now is None:
        return mp_goal
    if mp_goal is None:
        return mp_now
    stepped = mp_now - MP_PROGRESS_SEC_PER_WEEK * max(0, weeks_since_build)
    return max(mp_goal, stepped, mp_now - MP_MAX_GAIN_SEC)


def long_run_pace(mp: float, factor: float = LONG_PACE_FACTOR) -> float:
    """롱런 기본 페이스 = MP × 1.10~1.20(범위 밖 factor는 경계로 자른다)."""
    lo, hi = LONG_PACE_RANGE
    return mp * min(hi, max(lo, factor))


def long_mp_km(long_km: float, phase: str, position: float = 0.5) -> float:
    """롱런 안 MP 구간 거리. phase는 build/peak, position(0~1)은 비중 범위 안의 위치. 그 외 phase는 0."""
    share = MP_SHARE.get(phase)
    if share is None or long_km <= 0:
        return 0.0
    lo, hi = share
    return round(long_km * (lo + (hi - lo) * min(1.0, max(0.0, position))), 1)


def taper_week1_mp_km(long_km: float) -> float:
    """테이퍼 1주차 MP 구간: 10~13km, 롱런보다 길 수 없다."""
    return round(min(max(TAPER1_MP_KM[0], min(TAPER1_MP_KM[1], long_km * 0.5)), long_km), 1)


def race_week_session(warmup_km: float = 1.5) -> dict:
    """대회 주 수요일 세션: MP 3~5km, 워밍업·쿨다운 포함 총 6km 이상."""
    mp = RACE_WEEK_MP_KM[0]
    total = max(RACE_WEEK_MIN_TOTAL_KM, round(mp + warmup_km * 2, 1))
    return {"workout_type": "marathon", "mp_km": mp, "distance_km": total}
