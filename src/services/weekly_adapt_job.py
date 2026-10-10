"""주간 적응 잡 — 월요일 첫 계획 조회 때 지난주 결과로 이번 주 남은 planner 행을 갱신한다(v2 목표만, 멱등)."""
from __future__ import annotations

import json
import sqlite3
from datetime import date, timedelta

from src.training.goals import effective_rules_version, get_active_goal
from src.training.planner import generate_weekly_plan, get_vdot_adj, resolve_distance_label, save_weekly_plan


def _stored(conn: sqlite3.Connection, ds: str) -> dict | None:
    cur = conn.execute(
        "SELECT workout_type, distance_km, rationale, structure_json, completed, garmin_workout_id FROM planned_workouts"
        " WHERE date=? AND source='planner'", (ds,))
    row = cur.fetchone()
    return dict(zip([d[0] for d in cur.description], row)) if row else None


def run(conn: sqlite3.Connection, today: date | None = None) -> int:
    """오늘~이번 주 일요일의 미완료 planner 행 중 적응으로 바뀐 것만 다시 저장. 반환: 갱신 행 수."""
    from src.services.weekly_adapt_service import adapt_plan
    today = today or date.today()
    goal = get_active_goal(conn)
    ws = today - timedelta(days=today.weekday())
    if not goal or effective_rules_version(conn, goal["id"], ws) < 2:
        return 0
    base = generate_weekly_plan(conn, goal_id=goal["id"], week_start=ws)
    dlabel = resolve_distance_label(goal["distance_km"], goal.get("distance_label"))
    adapted = adapt_plan(conn, goal, base, ws, dlabel, get_vdot_adj(conn))
    changed = []
    for b, a in zip(base, adapted):
        if a["date"] < today.isoformat() or (a["workout_type"], a.get("distance_km"), a.get("rationale")) == \
                (b["workout_type"], b.get("distance_km"), b.get("rationale")):
            continue
        cur = _stored(conn, a["date"])
        if cur is None or cur["completed"] or cur["garmin_workout_id"]:
            continue
        new_struct = json.dumps(a["structure"]) if a.get("structure") else None
        if (cur["workout_type"], cur["distance_km"], cur["rationale"], cur["structure_json"]) == \
                (a["workout_type"], a.get("distance_km"), a.get("rationale"), new_struct):
            continue
        changed.append(a)
    return save_weekly_plan(conn, changed) if changed else 0
