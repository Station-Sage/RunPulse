"""계획 구간 교체(ADR-035 부록 R) — [start, end] 의 planner 행을 새 계획으로 바꾸되 이력이 있는 행은 지킨다.

보호 행(삭제 금지): completed=1 / matched_activity_id / session_outcomes.planned_id / 수락된 plan_adjustments.
삭제한 행의 proposed 조정은 함께 지운다. commit=False 가 기본이라 호출자가 SAVEPOINT·트랜잭션을 소유한다.
"""
from __future__ import annotations

import sqlite3

from .planner_store import write_planner_rows

_PROTECT_SQL = """
SELECT w.id,
  (w.completed = 1 OR w.matched_activity_id IS NOT NULL
   OR EXISTS (SELECT 1 FROM session_outcomes o WHERE o.planned_id = w.id)
   OR EXISTS (SELECT 1 FROM plan_adjustments a WHERE a.workout_id = w.id AND a.decision = 'accepted')) AS prot
FROM planned_workouts w WHERE w.source = 'planner' AND w.date >= ? AND w.date <= ?
"""
_GOAL_FILTER = " AND w.goal_id = ?"


def _row_dicts(conn: sqlite3.Connection, ids: list[int]) -> list[dict]:
    if not ids:
        return []
    cur = conn.execute(f"SELECT * FROM planned_workouts WHERE id IN ({','.join('?' * len(ids))}) ORDER BY date, id", ids)
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def replace_range(conn: sqlite3.Connection, plan: list[dict], start: str, end: str, commit: bool = False,
                  *, goal_id: int | None = None) -> dict:
    """[start, end](ISO, 양끝 포함) 의 planner 행을 plan 으로 교체. goal_id 가 있으면 그 목표 행만 지운다(None 이면 전체 목표).
    plan 을 넣으려면 goal_id 필수.

    Returns: {deleted: [행 dict], preserved: [행 dict], inserted: [id], snapshot: [삭제 행 dict],
              external: [{id, date, garmin_workout_id}], skipped_dates: [보호 행과 겹쳐 넣지 않은 날짜]}
    """
    rows = conn.execute(_PROTECT_SQL + (_GOAL_FILTER if goal_id is not None else ""),
                        (start, end) + ((goal_id,) if goal_id is not None else ())).fetchall()
    del_ids = [r[0] for r in rows if not r[1]]
    keep_ids = [r[0] for r in rows if r[1]]
    deleted = _row_dicts(conn, del_ids)
    preserved = _row_dicts(conn, keep_ids)
    if del_ids:
        ph = ",".join("?" * len(del_ids))
        conn.execute(f"DELETE FROM plan_adjustments WHERE workout_id IN ({ph}) AND decision != 'accepted'", del_ids)
        conn.execute(f"DELETE FROM planned_workouts WHERE id IN ({ph})", del_ids)
    kept_dates = {p["date"] for p in preserved}
    inserted: list[int] = []
    skipped: list[str] = []
    for w in plan:
        if not (start <= w["date"] <= end):
            continue
        if w["date"] in kept_dates:
            skipped.append(w["date"])
            continue
        inserted += write_planner_rows(conn, [w], goal_id=goal_id)
    if commit:
        conn.commit()
    external = [{"id": d["id"], "date": d["date"], "garmin_workout_id": d["garmin_workout_id"]}
                for d in deleted if d.get("garmin_workout_id")]
    return {"deleted": deleted, "preserved": preserved, "inserted": inserted, "snapshot": deleted,
            "external": external, "skipped_dates": skipped}
