"""훈련 계획 뷰 — 데이터 로더.

views_training.py에서 사용하는 DB 조회 함수 모음.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date, timedelta


def load_goal(conn: sqlite3.Connection) -> dict | None:
    """활성 목표 1건 조회."""
    from src.training.goals import get_active_goal
    return get_active_goal(conn)


def load_workouts(
    conn: sqlite3.Connection,
    week_offset: int = 0,
) -> tuple[list[dict], date]:
    """해당 주 운동 목록 + 주 시작일 반환.

    Args:
        week_offset: 0=이번주, -1=지난주, 1=다음주.

    Returns:
        (workouts, week_start)
    """
    from src.training.planner import get_planned_workouts

    today = date.today()
    week_start = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)
    workouts = get_planned_workouts(conn, week_start=week_start)
    return workouts, week_start


def load_adjustment(
    conn: sqlite3.Connection,
    config: dict | None = None,
) -> dict | None:
    """오늘 컨디션 조정 데이터."""
    from src.training.adjuster import adjust_todays_plan
    try:
        return adjust_todays_plan(conn, config)
    except Exception:
        return None


def _safe_json(raw) -> dict:
    """안전한 JSON 파싱."""
    if not raw:
        return {}
    try:
        return json.loads(raw) if isinstance(raw, str) else raw
    except (json.JSONDecodeError, TypeError):
        return {}


def load_training_metrics(conn: sqlite3.Connection) -> dict:
    """UTRS, CIRS 최신값 + JSON 로드.

    Returns:
        {"utrs_val": float|None, "utrs_json": dict,
         "cirs_val": float|None, "cirs_json": dict}
    """
    result: dict = {}
    for name in ("UTRS", "CIRS"):
        row = conn.execute(
            "SELECT metric_value, metric_json FROM computed_metrics "
            "WHERE metric_name = ? ORDER BY date DESC LIMIT 1",
            (name,),
        ).fetchone()
        key = name.lower()
        if row:
            result[f"{key}_val"] = row[0]
            result[f"{key}_json"] = _safe_json(row[1])
        else:
            result[f"{key}_val"] = None
            result[f"{key}_json"] = {}
    return result


def load_yesterday_pending(conn: sqlite3.Connection) -> dict | None:
    """어제 날짜의 미확인(완료도 건너뜀도 아닌) 계획 조회.

    Returns:
        미확인 워크아웃 dict (id, date, workout_type, distance_km, completed 포함),
        없으면 None.
    """
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    row = conn.execute(
        "SELECT id, date, workout_type, distance_km, completed "
        "FROM planned_workouts "
        "WHERE date=? AND workout_type != 'rest' AND completed = 0 "
        "ORDER BY id DESC LIMIT 1",
        (yesterday,),
    ).fetchone()
    if not row:
        return None
    return {
        "id": row[0], "date": row[1], "workout_type": row[2],
        "distance_km": row[3], "completed": row[4],
    }


def load_actual_activities(
    conn: sqlite3.Connection,
    week_start: date,
) -> dict[str, dict]:
    """주간 날짜별 실제 러닝 활동 조회.

    Returns:
        {"2026-03-25": {"id": 123, "km": 10.5, "pace": 305, "hr": 148}, ...}
    """
    from src.training.matcher import get_actual_activities_for_week
    try:
        return get_actual_activities_for_week(conn, week_start)
    except Exception:
        return {}


def load_sync_status(conn: sqlite3.Connection) -> list[dict]:
    """소스별 마지막 동기화 시각 조회.

    Returns:
        [{"service": "garmin", "last_sync": "2026-03-25 10:30", "status": "completed"}, ...]
    """
    rows = conn.execute(
        """SELECT service,
                  MAX(created_at) AS last_sync,
                  status
           FROM sync_jobs
           GROUP BY service
           ORDER BY service""",
    ).fetchall()
    return [
        {"service": r[0], "last_sync": r[1], "status": r[2]}
        for r in rows
    ]
