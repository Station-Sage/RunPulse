"""플랜 주간 개요(R3, PLN-1/5/7) — 목표의 전체 주를 한 표로: 단계·계획 거리·실제 거리·러닝/휴식일·롱런·품질·준수율.

계획 수치는 그 목표의 planner 행(휴식·대회 제외 거리 합)에서 읽어 planned_workouts 합계와 일치한다.
시작 주가 부분 주면 start_date 에 첫 계획일을 실어 줄어든 목표임을 표시한다. 실제 거리는 어제까지 집계한다.
"""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from src.training import week_compliance
from src.training.goals import get_goal
from src.training.planner_config import get_vdot_adj
from src.training.planner_rules import plan_start_monday, resolve_distance_label
from src.training.planner_schedule import schedule_for_goal

BASIS = {"scope": "week", "label": "이번 주"}


def _phases(conn: sqlite3.Connection, goal: dict, today: date) -> dict[str, str]:
    start = plan_start_monday(goal.get("race_date"), goal.get("plan_weeks"))
    if start is None:
        return {}
    dlabel = resolve_distance_label(goal["distance_km"], goal.get("distance_label"))
    sched = schedule_for_goal(conn, goal, dlabel, get_vdot_adj(conn), today)
    return {(start + timedelta(weeks=t.index)).isoformat(): t.phase for t in sched}


def get_plan_overview(conn: sqlite3.Connection, goal_id: int, today: date | None = None) -> dict | None:
    """목표가 없으면 None. weeks 는 월요일 시작 주 목록(계획 행이 없으면 빈 리스트)."""
    goal = get_goal(conn, goal_id)
    if goal is None:
        return None
    today = today or date.today()
    rows = conn.execute(
        "SELECT date, workout_type, distance_km FROM planned_workouts WHERE source='planner' AND goal_id=? ORDER BY date",
        (goal_id,)).fetchall()
    by_week: dict[str, list[tuple]] = {}
    for d, t, km in rows:
        ds = date.fromisoformat(d)
        by_week.setdefault((ds - timedelta(days=ds.weekday())).isoformat(), []).append((d, t, km or 0.0))
    phases = _phases(conn, goal, today)
    weeks = []
    for ws, items in sorted(by_week.items()):
        mon = date.fromisoformat(ws)
        runs = [i for i in items if i[1] not in ("rest", "race")]
        past_end = min(mon + timedelta(days=6), today - timedelta(days=1))
        comp = actual = None
        if past_end >= mon:
            comp = week_compliance.compute(conn, mon, past_end, mon, today, goal_id)["compliance"]["volume"]
            actual = comp["actual_km"]
        weeks.append({
            "week_start": ws, "start_date": items[0][0] if items[0][0] > ws else None,
            "phase": phases.get(ws), "planned_km": round(sum(i[2] for i in runs), 1), "actual_km": actual,
            "run_days": len(runs), "rest_days": len(items) - len(runs),
            "long_km": max((i[2] for i in runs if i[1] in ("long", "long_mp")), default=0.0),
            "quality_n": sum(1 for i in runs if i[1] in week_compliance.QUALITY_TYPES),
            "compliance_pct": comp["pct"] if comp else None,
        })
    return {"goal_id": goal_id, "weeks": weeks, "basis": BASIS}
