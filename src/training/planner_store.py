"""planner 행 저장 단일 진입점(PLN-38) — planned_workouts 에 source='planner' 행을 넣는 유일한 경로.

v40 CHECK(source<>'planner' OR goal_id IS NOT NULL)가 goal_id 누락을 막고, 이 모듈이 goal_id 를 강제한다.
저장 시 같은 날짜의 같은 목표 planner 행만 지운다(다른 목표 행은 건드리지 않음).
"""
from __future__ import annotations

import json
import sqlite3

_STD_COLS = (
    "date", "workout_type", "distance_km", "target_pace_min", "target_pace_max", "target_hr_zone",
    "description", "rationale", "source", "interval_prescription", "structure_json",
)


def _std_values(w: dict) -> list:
    return [
        w["date"], w["workout_type"], w.get("distance_km"), w.get("target_pace_min"), w.get("target_pace_max"),
        w.get("target_hr_zone"), w.get("description"), w.get("rationale"), w.get("source", "planner"),
        w.get("interval_prescription"), json.dumps(w["structure"]) if w.get("structure") else None,
    ]


def write_planner_rows(conn: sqlite3.Connection, rows: list[dict], *, goal_id: int, restore: bool = False) -> list[int]:
    """planner 행 INSERT. goal_id 필수. restore=True 면 rows 의 모든 컬럼(id 포함)을 그대로 복원한다(replan undo).

    Returns: 새로 생긴 행 id 목록.
    """
    if goal_id is None:
        raise ValueError("goal_id 가 필요합니다 (planner 행은 목표에 속함)")
    ids: list[int] = []
    for w in rows:
        if restore:
            d = {**w, "goal_id": goal_id}
            cols = list(d)
            cur = conn.execute(
                f"INSERT INTO planned_workouts({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
                [d[c] for c in cols])
        else:
            cur = conn.execute(
                f"INSERT INTO planned_workouts({','.join(_STD_COLS)}, goal_id)"
                f" VALUES ({','.join('?' * (len(_STD_COLS) + 1))})",
                _std_values(w) + [goal_id])
        ids.append(cur.lastrowid)
    return ids


def resolve_goal_id(conn: sqlite3.Connection, goal_id: int | None) -> int:
    """goal_id 가 없으면 활성 목표. 둘 다 없으면 ValueError."""
    if goal_id is not None:
        return goal_id
    row = conn.execute(
        "SELECT id FROM goals WHERE status='active' ORDER BY created_at DESC, id DESC LIMIT 1").fetchone()
    if not row:
        raise ValueError("활성 목표가 없어 planner 행을 저장할 수 없습니다")
    return row[0]


def save_weekly_plan(conn: sqlite3.Connection, plan: list[dict], commit: bool = True, *, goal_id: int | None = None) -> int:
    """주간 계획 저장 — 같은 목표의 같은 날짜 planner 행을 지우고 다시 넣는다. goal_id 없으면 활성 목표.

    Returns: 저장된 레코드 수.
    """
    if not plan:
        return 0
    gid = resolve_goal_id(conn, goal_id)
    for w in plan:
        conn.execute("DELETE FROM planned_workouts WHERE date = ? AND source = 'planner' AND goal_id = ?",
                     (w["date"], gid))
    count = len(write_planner_rows(conn, plan, goal_id=gid))
    if commit:
        conn.commit()
    return count
