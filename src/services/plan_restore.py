"""과거 플랜 복원(PLN-43) — 취소된 목표의 plan_snapshot_json 행을 되살리고 그 목표를 활성으로 되돌린다.

현재 활성 목표는 cancelled 가 되고, 그 미래 행(이력 없는 것)은 스냅샷으로 저장된다.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date

from src.services.plan_template_service import _UNSET, check_active_expectation
from src.training.goals import get_goal
from src.training.plan_replace import replace_range
from src.training.planner_store import write_planner_rows
from src.training.rematch import rematch_goal


class RestoreError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def restore_plan(conn: sqlite3.Connection, goal_id: int, expect_active_goal_id=_UNSET) -> dict:
    """goal_id 플랜 복원. 반환 {goal_id, restored}. 복원 불가면 RestoreError(NOT_FOUND|NOT_RESTORABLE)."""
    goal = get_goal(conn, goal_id)
    if goal is None:
        raise RestoreError("NOT_FOUND", "목표가 없습니다")
    blob = conn.execute("SELECT plan_snapshot_json FROM goals WHERE id=?", (goal_id,)).fetchone()[0]
    if goal["status"] == "active" or not blob:
        raise RestoreError("NOT_RESTORABLE", "복원할 수 있는 스냅샷이 없습니다")
    rows = json.loads(blob)
    prev = check_active_expectation(conn, expect_active_goal_id)
    today = date.today().isoformat()
    conn.execute("SAVEPOINT restore_plan")
    try:
        if prev is not None:
            res = replace_range(conn, [], today, "9999-12-31", goal_id=prev["id"])
            conn.execute("UPDATE goals SET plan_snapshot_json=?, status='cancelled' WHERE id=?",
                         (json.dumps(res["snapshot"], ensure_ascii=False, default=str), prev["id"]))
        conn.execute("UPDATE goals SET status='active', plan_snapshot_json=NULL WHERE id=?", (goal_id,))
        occupied = {r[0] for r in conn.execute("SELECT date FROM planned_workouts WHERE date>=?", (today,))}
        keep = [{k: v for k, v in r.items() if k != "goal_id"} for r in rows
                if r["date"] >= today and r["date"] not in occupied]
        write_planner_rows(conn, [{k: v for k, v in r.items() if k != "id"} for r in keep],
                           goal_id=goal_id, restore=True)
        conn.execute("RELEASE restore_plan")
    except Exception:
        conn.execute("ROLLBACK TO restore_plan")
        conn.execute("RELEASE restore_plan")
        raise
    conn.commit()
    rematch_goal(conn, goal_id)
    return {"goal_id": goal_id, "restored": len(keep)}
