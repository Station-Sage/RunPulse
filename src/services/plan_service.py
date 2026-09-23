"""Phase 7b 서비스 레이어 - 훈련 플랜 조회 (진행 중 플랜 + 오늘 조정).

get_active_plan() — 활성 목표 + 이번 주 워크아웃 + 피트니스 조합.
get_todays_adjustment() — adjust_todays_plan() 위임.
get_session_detail() — 특정 날짜 세션 상세 (조정 포함).
get_session_note() / save_session_note() — 세션 메모 CRUD.
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


def _plan_date_range(goal: dict) -> tuple[str | None, str | None]:
    """이 목표의 planned_workouts 조회 범위: [created_at 주 월요일, race_date].

    planned_workouts에 goal_id 컬럼이 없어 source='planner'만으로는 여러 목표의
    워크아웃이 뒤섞인다 — created_at/race_date로 날짜 범위를 좁혀 다른 목표(완료/취소된
    이전 목표 포함)의 데이터가 섞이지 않게 한다.
    """
    start = None
    created_at = goal.get("created_at")
    if created_at:
        try:
            created = date.fromisoformat(created_at[:10])
            start = (created - timedelta(days=created.weekday())).isoformat()
        except (ValueError, TypeError):
            pass
    return start, goal.get("race_date")


def _week_index_for_date(goal: dict, target_date: date) -> int:
    """1-based 주 인덱스 (목표 생성 주 기준, target_date의 월요일 기준)."""
    start, _ = _plan_date_range(goal)
    if not start:
        return 1
    try:
        start_date = date.fromisoformat(start)
        ws = target_date - timedelta(days=target_date.weekday())
        weeks = max(0, (ws - start_date).days // 7)
        return weeks + 1
    except (ValueError, TypeError):
        return 1


def _week_index_absolute(conn: sqlite3.Connection, goal: dict) -> int:
    """1-based 절대 주 인덱스 (목표 생성 주 기준)."""
    return _week_index_for_date(goal, date.today())


def _compliance_pct(conn: sqlite3.Connection, goal: dict) -> float | None:
    """완료된 / 비-휴식 워크아웃 비율 (이 목표의 플랜 기간 내)."""
    start, end = _plan_date_range(goal)
    clauses = ["source='planner'"]
    params: list[str] = []
    if start:
        clauses.append("date >= ?")
        params.append(start)
    if end:
        clauses.append("date <= ?")
        params.append(end)
    rows = conn.execute(
        f"SELECT workout_type, completed FROM planned_workouts WHERE {' AND '.join(clauses)}",
        params,
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
    week_index = _week_index_absolute(conn, goal)
    compliance_pct = _compliance_pct(conn, goal)
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


def get_session_detail(
    conn: sqlite3.Connection, goal_id: int, session_date: str
) -> dict | None:
    """특정 날짜의 세션 상세 반환.

    Args:
        conn: SQLite 연결.
        goal_id: 목표 ID.
        session_date: ISO 날짜 문자열 (URL에서 옴).

    Returns:
        {goal, week_index, workout, adjustment, note} or None.
    """
    goal = get_goal(conn, goal_id)
    if goal is None:
        return None

    try:
        sd = date.fromisoformat(session_date)
    except (ValueError, TypeError):
        return None

    week_start = sd - timedelta(days=sd.weekday())
    workouts = get_planned_workouts(conn, week_start=week_start)
    workout = next((w for w in workouts if w.get("date") == session_date), None)
    if workout is None:
        return None

    week_index = _week_index_for_date(goal, sd)
    adjustment = adjust_todays_plan(conn, date=session_date)
    note = get_session_note(conn, session_date)

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
        "workout": workout,
        "adjustment": adjustment,
        "note": note,
    }


def get_session_note(conn: sqlite3.Connection, session_date: str) -> str | None:
    """세션 메모 조회."""
    row = conn.execute(
        "SELECT note FROM user_inputs WHERE input_date = ? AND input_type = 'session_note'",
        (session_date,),
    ).fetchone()
    return row[0] if row else None


def save_session_note(conn: sqlite3.Connection, session_date: str, note: str) -> None:
    """세션 메모 저장 (UPSERT)."""
    conn.execute(
        """INSERT INTO user_inputs (input_date, input_type, note)
           VALUES (?, 'session_note', ?)
           ON CONFLICT(input_date, input_type) DO UPDATE SET note = excluded.note""",
        (session_date, note),
    )
    conn.commit()
