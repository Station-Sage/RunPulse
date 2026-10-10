"""주간 적응 잡 — 계획 조회 때 지난주 결과(적응)와 예보 폭염(페이스만, E10)으로 이번 주 남은 planner 행을 갱신한다(v2 목표만, 멱등)."""
from __future__ import annotations

import json
import sqlite3
from datetime import date, timedelta

from src.services.heat_forecast import forecast_heat_pct
from src.training.constraints import heat_adjust
from src.training.goals import effective_rules_version, get_active_goal
from src.training.planner import generate_weekly_plan, get_vdot_adj, resolve_distance_label, save_weekly_plan


def _stored(conn: sqlite3.Connection, ds: str) -> dict | None:
    cur = conn.execute(
        "SELECT workout_type, distance_km, rationale, structure_json, target_pace_min, target_pace_max, completed, garmin_workout_id FROM planned_workouts"
        " WHERE date=? AND source='planner'", (ds,))
    row = cur.fetchone()
    return dict(zip([d[0] for d in cur.description], row)) if row else None


def _sig(r: dict) -> tuple:
    return (r["workout_type"], r.get("distance_km"), r.get("rationale"), r.get("target_pace_min"), r.get("target_pace_max"))


def run(conn: sqlite3.Connection, today: date | None = None, getter=None) -> int:
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
    if getter is None:
        from src.utils.api import get as getter
    adapted = heat_adjust(adapted, forecast_heat_pct(conn, getter, today), swap=False)
    by_date = {a["date"]: a for a in adapted}
    changed = []
    for b in base:
        a = by_date[b["date"]]
        if a["date"] < today.isoformat() or _sig(a) == _sig(b):
            continue
        cur = _stored(conn, a["date"])
        if cur is None or cur["completed"] or cur["garmin_workout_id"]:
            continue
        new_struct = json.dumps(a["structure"]) if a.get("structure") else None
        if (*_sig(cur), cur["structure_json"]) == (*_sig(a), new_struct):
            continue
        changed.append(a)
    return save_weekly_plan(conn, changed) if changed else 0
