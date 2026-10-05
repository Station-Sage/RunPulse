"""계획 준비 볼륨·경고 — 피크 롱런 하한을 담을 주간 거리에 대회 전까지 닿는지 판정한다 (DESIGN-U16-LONGRUN §5.2-5).

순수 함수(ready_week_km·cold_peak_km·readiness_warning)와, 목표 하나의 일정을 만들어 경고를 모으는 DB 래퍼(plan_warnings)로 나뉜다.
"""
from __future__ import annotations

import sqlite3
from datetime import date

from . import long_run_rules as LR
from .periodization import WeekTarget

COLD_PEAK_SHARE = 0.50      # 콜드 피크 목표: 피크 하한 롱런이 주간의 절반(풀 build/peak 비중 R_FULL)이 되는 주간
DIST_NAME = {"full": "풀마라톤", "half": "하프마라톤", "10k": "10km", "5k": "5km"}


def _peak_floor(dlabel: str) -> float:
    return LR.PHASE_FLOOR[dlabel if dlabel in LR.PHASE_FLOOR else "10k"]["peak"]


def _km(x: float) -> str:
    """12.0 → "12", 14.5 → "14.5"."""
    return f"{x:.1f}".removesuffix(".0")


def ready_week_km(dlabel: str) -> float:
    """준비 볼륨 = 피크 단계 하한 롱런 ÷ 외피 0.6(주 3일 이상). 풀 40, 하프 26.7, 10k 23.3, 5k 16.7."""
    return round(_peak_floor(dlabel) / LR.ENV_HIGH_DAYS, 1)


def cold_peak_km(dlabel: str) -> float:
    """v2 콜드스타트 피크 목표 주간 km = 피크 하한 ÷ 0.5. 풀 48, 하프 32, 10k 28, 5k 20."""
    return round(_peak_floor(dlabel) / COLD_PEAK_SHARE, 1)


def readiness_warning(dlabel: str, sched: list[WeekTarget], max_week_km: float | None = None) -> str | None:
    """일정의 최대 주간(감량 전)이 준비 볼륨에 못 미치면 한국어 경고, 닿으면 None. 일정이 없으면 None."""
    train = [w.weekly_km for w in sched if w.phase != "taper"]
    if not train:
        return None
    ready, peak = ready_week_km(dlabel), max(train)
    if peak >= ready - 0.05:
        return None
    name = DIST_NAME.get(dlabel, "대회")
    if max_week_km is not None and max_week_km < ready - 0.05:
        return (f"지금 러닝 일수로 소화할 수 있는 주간 거리(최대 {_km(max_week_km)}km)로는 {name} 준비 볼륨"
                f"(주 {_km(ready)}km)에 닿기 어렵습니다. 러닝 일수를 늘리는 것을 고려하세요.")
    return (f"현재 주 {_km(sched[0].weekly_km)}km로는 {len(sched)}주 안에 {name} 준비 볼륨(주 {_km(ready)}km)에 "
            f"닿기 어렵습니다. 주 10%씩 늘려도 최대 주 {_km(peak)}km입니다.")


def plan_warnings(conn: sqlite3.Connection, goal_id: int, today: date | None = None) -> list[str]:
    """목표의 주기화 일정으로 계획 생성 경고 목록을 만든다. 목표·일정이 없으면 빈 리스트."""
    from .goals import get_goal
    from .planner_config import get_vdot_adj
    from .planner_rules import resolve_distance_label
    from .planner_schedule import schedule_for_goal, week_cap_km
    goal = get_goal(conn, goal_id)
    if goal is None:
        return []
    dlabel = resolve_distance_label(goal.get("distance_km") or 10.0, goal.get("distance_label"))
    vdot = get_vdot_adj(conn)
    sched = schedule_for_goal(conn, goal, dlabel, vdot, today)
    msg = readiness_warning(dlabel, sched, week_cap_km(conn, goal, dlabel, vdot))
    return [msg] if msg else []
