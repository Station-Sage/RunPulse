"""Phase 7b 서비스 레이어 - 훈련 플랜 조회 (진행 중 플랜 + 오늘 조정).

get_active_plan() — 활성 목표 + 이번 주 워크아웃 + 피트니스 조합.
get_todays_adjustment() — adjust_todays_plan() 위임.
get_session_detail() — 특정 날짜 세션 상세 (조정 포함).
get_session_note() / save_session_note() — 세션 메모 CRUD.
"""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from src.training import week_compliance
from src.training.adjuster import adjust_todays_plan
from src.training.goals import get_active_goal, get_goal
from src.training.planner import get_planned_workouts
from src.training.planner_rules import plan_start_monday
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
    planned = plan_start_monday(goal.get("race_date"), goal.get("plan_weeks"))
    if planned is not None:                      # 대회 역산 계획: 시작 = 대회 주 - (plan_weeks-1)주
        return planned.isoformat(), goal.get("race_date")
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
        return (ws - start_date).days // 7 + 1      # 시작 전이면 0 이하
    except (ValueError, TypeError):
        return 1


def _week_index_absolute(conn: sqlite3.Connection, goal: dict) -> int:
    """1-based 절대 주 인덱스 (목표 생성 주 기준)."""
    return _week_index_for_date(goal, date.today())


def _effective_start(goal: dict) -> date | None:
    """이행 집계 시작일 = max(계획 시작일, 목표 생성일) — 계획이 생기기 전 날짜는 분모에 넣지 않는다(R2)."""
    start, _ = _plan_date_range(goal)
    cands = []
    for v in (start, (goal.get("created_at") or "")[:10]):
        try:
            cands.append(date.fromisoformat(v))
        except (ValueError, TypeError):
            pass
    return max(cands) if cands else None


def _plan_compliance(conn: sqlite3.Connection, goal: dict, today: date | None = None) -> dict | None:
    """계획 시작부터 오늘까지 이행 수치(세션·볼륨·품질) — src/training/week_compliance.py R1~R3."""
    today = today or date.today()
    eff_start = _effective_start(goal)
    if eff_start is None or eff_start > today:
        return None
    return week_compliance.compute(conn, eff_start, today, eff_start, today)["compliance"]


def _compliance_pct(conn: sqlite3.Connection, goal: dict) -> float | None:
    """세션 이행률(%) — 기존 필드 호환용. 표시는 compliance{sessions, volume, quality}를 쓴다."""
    c = _plan_compliance(conn, goal)
    if not c or not c["sessions"]["total"]:
        return None
    return round(c["sessions"]["done"] / c["sessions"]["total"] * 100, 1)


def _next_session(conn: sqlite3.Connection) -> dict | None:
    """오늘 이후 첫 미완료 세션(이번 주 → 다음 주). 휴식·완료·대체된 추천안은 건너뛴다."""
    ws = _current_week_start()
    today = date.today().isoformat()
    for w in (ws, ws + timedelta(weeks=1)):
        for row in get_planned_workouts(conn, week_start=w):
            if (row["date"] >= today and row["workout_type"] != "rest"
                    and not row["completed"] and not row["superseded"]):
                return row
    return None


def get_active_plan(conn: sqlite3.Connection, goal_id: int | None = None) -> dict | None:
    """활성 플랜 조합 반환.

    Returns:
        {goal, week_index, workouts, ctl_current, compliance_pct, next_session} or None.
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
    week = week_compliance.compute(conn, week_start, week_start + timedelta(days=6),
                                   _effective_start(goal))
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
        "compliance": _plan_compliance(conn, goal),
        "week": week,
        "next_session": _next_session(conn),
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
