"""재계획 anchor 접기(순수 + 조회) — plan_replans 의 적용된 anchor 이후 주만 새 시작 부하로 다시 만든 일정으로 바꾼다(ADR-035 부록 R).

anchor 이전 주는 원래 일정 그대로이고 주 index 는 원래 계획 시작 기준이라, 주차 표기·준수율·진행 상한이 바뀌지 않는다.
anchor 가 없으면 입력 일정을 그대로 돌려준다(기존 동작과 동일).
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, replace
from datetime import date
from typing import Callable

from .periodization import WeekTarget


@dataclass(frozen=True)
class Anchor:
    anchor_monday: date
    start_km: float
    start_long_km: float | None = None
    target_time_sec: int | None = None
    id: int | None = None
    start_source: str = "user"
    rules_version: int | None = None


# build_tail(anchor, remaining_weeks) → anchor 주부터 대회 주까지의 일정(index 는 0 부터)
TailBuilder = Callable[[Anchor, int], list[WeekTarget]]


def load_anchors(conn: sqlite3.Connection, goal_id: int | None) -> list[Anchor]:
    """goal 의 적용된(applied) anchor 를 anchor_monday 순으로. 테이블이 없거나 goal 이 없으면 빈 리스트."""
    if goal_id is None:
        return []
    try:
        rows = conn.execute(
            "SELECT id, anchor_monday, start_km, start_long_km, target_time_sec, start_source, rules_version FROM plan_replans "
            "WHERE goal_id = ? AND status = 'applied' ORDER BY anchor_monday, id", (goal_id,)).fetchall()
    except sqlite3.OperationalError:
        return []
    return [Anchor(date.fromisoformat(r[1]), float(r[2]), r[3], r[4], r[0], r[5] or "user", r[6]) for r in rows]


def fold(base: list[WeekTarget], plan_start: date, anchors: list[Anchor], build_tail: TailBuilder) -> list[WeekTarget]:
    """base 일정에 anchor 를 차례로 접는다. anchor 가 범위 밖(시작 이전은 0 주차로, 대회 주 이후는 무시)이면 보정·건너뜀."""
    out = list(base)
    total = len(base)
    for a in sorted(anchors, key=lambda x: (x.anchor_monday, x.id or 0)):
        idx = max(0, (a.anchor_monday - plan_start).days // 7)
        if idx >= total:
            continue
        tail = build_tail(a, total - idx)
        if not tail:
            continue
        out = out[:idx] + [replace(w, index=idx + w.index) for w in tail]
    return out
