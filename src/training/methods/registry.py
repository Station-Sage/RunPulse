"""PlanMethod 정의·레지스트리와 목표별 유효 방식 조회."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Callable

DEFAULT_METHOD = "balanced"


@dataclass(frozen=True)
class PlanMethod:
    id: str
    label: str
    summary: str
    distances: frozenset[str]            # resolve_distance_label 결과 ('10k','half','full' 등)
    pros: tuple[str, ...] = ()
    cons: tuple[str, ...] = ()
    target_runners: str = ""
    sources: tuple[str, ...] = ()
    min_run_days: int = 1                # 후보 가드: 선택 가능 러닝 요일이 이보다 적으면 후보 제외
    adjust: Callable[[list[dict], dict], list[dict]] | None = None   # 주간 계획 후처리 훅(balanced 는 None=무변경)


METHODS: dict[str, PlanMethod] = {
    "balanced": PlanMethod(
        id="balanced", label="균형형(기본)",
        summary="80/20 강도 배분과 Q-day 기반 현행 규칙. 대회 역산 주기화.",
        distances=frozenset({"5k", "10k", "half", "full"}),
        pros=("부상 위험이 낮음", "검증된 기본 구성"), cons=("거리별 특이성은 보통",),
        target_runners="처음이거나 어떤 방식이 맞는지 모르는 러너",
        sources=("planner v2 (papers-based)",),
    ),
}


def get_method(method_id: str | None) -> PlanMethod:
    """알 수 없거나 비어 있으면 balanced."""
    return METHODS.get(method_id or DEFAULT_METHOD, METHODS[DEFAULT_METHOD])


def candidates_for(distance_label: str, run_days: int | None = None) -> list[PlanMethod]:
    """거리·러닝 요일 수 하드 가드를 통과한 방식(추천 후보). 경고성 부적합은 여기서 거르지 않는다."""
    out = [m for m in METHODS.values()
           if distance_label in m.distances and (run_days is None or run_days >= m.min_run_days)]
    return out or [METHODS[DEFAULT_METHOD]]


def goal_method(conn: sqlite3.Connection, goal_id: int | None) -> str:
    """goals.plan_method (컬럼·행이 없으면 balanced)."""
    if goal_id is None:
        return DEFAULT_METHOD
    try:
        row = conn.execute("SELECT plan_method FROM goals WHERE id = ?", (goal_id,)).fetchone()
    except sqlite3.OperationalError:
        return DEFAULT_METHOD
    return get_method(row[0] if row else None).id


def effective_method(conn: sqlite3.Connection, goal_id: int | None, week_start=None) -> str:
    """주 기준 유효 방식: 그 주 이전(포함) 마지막 applied 재계획 anchor 의 plan_method, 없으면 목표 값.

    week_start 가 None 이면 날짜와 무관하게 마지막 applied anchor 를 쓴다(과거 주는 과거 방식 유지, undo 는 status 로 반영)."""
    if goal_id is None:
        return DEFAULT_METHOD
    q = "SELECT plan_method FROM plan_replans WHERE goal_id = ? AND status = 'applied' AND plan_method IS NOT NULL"
    args: list = [goal_id]
    if week_start is not None:
        q += " AND anchor_monday <= ?"
        args.append(week_start.isoformat() if hasattr(week_start, "isoformat") else week_start)
    try:
        row = conn.execute(q + " ORDER BY anchor_monday DESC, id DESC LIMIT 1", args).fetchone()
    except sqlite3.OperationalError:
        row = None
    return get_method(row[0]).id if row else goal_method(conn, goal_id)
