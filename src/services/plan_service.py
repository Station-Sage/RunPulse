"""Phase 7b 서비스 레이어 - 훈련 플랜 조회 (진행 중 플랜 + 오늘 조정).

get_active_plan() — 활성 목표 + 이번 주 워크아웃 + 피트니스 조합.
get_todays_adjustment() — adjust_todays_plan() 위임.
"""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from src.training.adjuster import adjust_todays_plan
from src.training.goals import get_active_goal, get_goal
from src.training.planner import get_planned_workouts
from src.training.planner_config import get_latest_fitness


def _current_week_start() -> date:
    today = date.today()
    return today - timedelta(days=today.weekday())


def _week_index_absolute(conn: sqlite3.Connection) -> int:
    """1-based 절대 주 인덱스 (최초 planner 워크아웃 기준)."""
    row = conn.execute(
        "SELECT MIN(date) FROM planned_workouts WHERE source='planner'"
    ).fetchone()
    earliest = row[0] if row else None
    if not earliest:
        return 1
    try:
        start = date.fromisoformat(earliest[:10])
        ws = _current_week_start()
        weeks = max(0, (ws - start).days // 7)
        return weeks + 1
    except (ValueError, TypeError):
        return 1


def _compliance_pct(conn: sqlite3.Connection) -> float | None:
    """완료된 / 비-휴식 워크아웃 비율 (전체 기간)."""
    rows = conn.execute(
        "SELECT workout_type, completed FROM planned_workouts WHERE source='planner'"
    ).fetchall()
    non_rest = [r for r in rows if r[0] != "rest"]
    if not non_rest:
        return None
    completed = sum(1 for r in non_rest if r[1])
    return round(completed / len(non_rest) * 100, 1)


def get_active_plan(conn: sqlite3.Connection, goal_id: int | None = None) -> dict | None:
    """활성 플랜 조합 반환.

    Returns:
        {goal, week_index, workouts, ctl_current, compliance_pct} or None.
    """
    goal = get_goal(conn, goal_id) if goal_id is not None else get_active_goal(conn)
    if goal is None:
        return None
    week_start = _current_week_start()
    workouts = get_planned_workouts(conn, week_start=week_start)
    fitness = get_latest_fitness(conn)
    ctl_current = fitness.get("ctl")
    week_index = _week_index_absolute(conn)
    compliance_pct = _compliance_pct(conn)
    return {
        "goal": {
            "id": goal["id"],
            "name": goal["name"],
            "race_date": goal["race_date"],
            "distance_km": goal["distance_km"],
            "target_time_sec": goal["target_time_sec"],
            "plan_weeks": goal["plan_weeks"],
            "status": goal["status"],
        },
        "week_index": week_index,
        "workouts": workouts,
        "ctl_current": ctl_current,
        "compliance_pct": compliance_pct,
    }


def get_todays_adjustment(conn: sqlite3.Connection) -> dict | None:
    """오늘 워크아웃 조정 반환. 플랜 없으면 None."""
    return adjust_todays_plan(conn)
