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
    end_date: date | None = None,
) -> dict[str, dict]:
    """날짜별 실제 러닝 활동 조회.

    Args:
        end_date: None이면 week_start 기준 1주, 지정하면 그 범위까지.

    Returns:
        {"2026-03-25": {"id": 123, "km": 10.5, "pace": 305, "hr": 148}, ...}
    """
    from src.training.matcher import get_actual_activities_for_week
    try:
        if end_date is None:
            return get_actual_activities_for_week(conn, week_start)
        # 복수 주: 1주씩 순회 후 병합
        result: dict[str, dict] = {}
        cur = week_start
        while cur < end_date:
            result.update(get_actual_activities_for_week(conn, cur))
            cur += timedelta(weeks=1)
        return result
    except Exception:
        return {}


def load_month_workouts(
    conn: sqlite3.Connection,
    week_offset: int = 0,
) -> list[tuple[list[dict], date]]:
    """4주치 워크아웃 반환 — 월간 캘린더용.

    Returns:
        [(workouts, week_start), ...] — 4개 (week_offset 기준 시작)
    """
    from src.training.planner import get_planned_workouts

    today = date.today()
    base_week = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)

    result = []
    for i in range(4):
        ws = base_week + timedelta(weeks=i)
        workouts = get_planned_workouts(conn, week_start=ws)
        result.append((workouts, ws))
    return result


def load_full_plan_weeks(
    conn: sqlite3.Connection,
    goal: dict | None,
) -> list[dict]:
    """전체 기간 planned_workouts를 주별로 그룹화해 반환.

    Returns:
        list of {week_start, is_current, workouts, total_km,
                 total_count, completed_count}
    """
    from collections import defaultdict

    today = date.today()
    today_week = today - timedelta(days=today.weekday())

    # 기간 끝: 레이스 날짜 + 1주 또는 12주 앞
    if goal and goal.get("race_date"):
        try:
            end_date = date.fromisoformat(goal["race_date"]) + timedelta(days=7)
        except ValueError:
            end_date = today + timedelta(weeks=12)
    else:
        end_date = today + timedelta(weeks=12)

    # 기간 시작: DB 최초 워크아웃 (최대 52주 전까지)
    row = conn.execute(
        "SELECT MIN(date) FROM planned_workouts WHERE date >= ?",
        ((today - timedelta(weeks=52)).isoformat(),),
    ).fetchone()
    if row and row[0]:
        try:
            earliest = date.fromisoformat(row[0])
            start_week = earliest - timedelta(days=earliest.weekday())
        except ValueError:
            start_week = today_week
    else:
        start_week = today_week

    rows = conn.execute(
        """SELECT id, date, workout_type, distance_km,
                  target_pace_min, target_pace_max,
                  description, completed, source
           FROM planned_workouts
           WHERE date >= ? AND date < ?
           ORDER BY date""",
        (start_week.isoformat(), end_date.isoformat()),
    ).fetchall()

    keys = ["id", "date", "workout_type", "distance_km",
            "target_pace_min", "target_pace_max",
            "description", "completed", "source"]
    workouts = [dict(zip(keys, r)) for r in rows]

    week_map: dict[str, list] = defaultdict(list)
    for w in workouts:
        d = date.fromisoformat(w["date"])
        ws = (d - timedelta(days=d.weekday())).isoformat()
        week_map[ws].append(w)

    weeks = []
    for ws_iso in sorted(week_map.keys()):
        ws = date.fromisoformat(ws_iso)
        wlist = week_map[ws_iso]
        non_rest = [w for w in wlist if w.get("workout_type") != "rest"]
        total_km = sum(w.get("distance_km") or 0 for w in wlist)
        completed = sum(1 for w in non_rest if w.get("completed") == 1)
        weeks.append({
            "week_start": ws,
            "is_current": ws == today_week,
            "workouts": wlist,
            "total_km": total_km,
            "total_count": len(non_rest),
            "completed_count": completed,
        })

    return weeks


def load_goals_with_stats(conn: sqlite3.Connection) -> list[dict]:
    """전체 목표 목록 + 수행률 통계.

    Returns:
        goals list — 각 dict에 completed_count, total_count 추가.
    """
    from src.training.goals import list_goals
    goals = list_goals(conn, status="all")
    for g in goals:
        start, end = _goal_date_range(g)
        row = conn.execute(
            """SELECT
                COUNT(CASE WHEN workout_type != 'rest' THEN 1 END),
                COUNT(CASE WHEN completed = 1 AND workout_type != 'rest' THEN 1 END)
               FROM planned_workouts WHERE date >= ? AND date <= ?""",
            (start, end),
        ).fetchone()
        g["total_count"] = row[0] if row else 0
        g["completed_count"] = row[1] if row else 0
    return goals


def load_goal_weeks(
    conn: sqlite3.Connection,
    goal: dict,
) -> list[dict]:
    """목표 기간의 planned_workouts를 주별로 그룹화.

    Returns:
        list of {week_start, is_current, workouts, total_km,
                 total_count, completed_count}
    """
    from collections import defaultdict

    today = date.today()
    today_week = today - timedelta(days=today.weekday())
    start, end = _goal_date_range(goal)

    rows = conn.execute(
        """SELECT id, date, workout_type, distance_km, completed
           FROM planned_workouts
           WHERE date >= ? AND date <= ?
           ORDER BY date""",
        (start, end),
    ).fetchall()
    keys = ["id", "date", "workout_type", "distance_km", "completed"]
    workouts = [dict(zip(keys, r)) for r in rows]

    week_map: dict[str, list] = defaultdict(list)
    for w in workouts:
        d = date.fromisoformat(w["date"])
        ws = (d - timedelta(days=d.weekday())).isoformat()
        week_map[ws].append(w)

    weeks = []
    for ws_iso in sorted(week_map.keys()):
        ws = date.fromisoformat(ws_iso)
        wlist = week_map[ws_iso]
        non_rest = [w for w in wlist if w.get("workout_type") != "rest"]
        total_km = sum(w.get("distance_km") or 0 for w in wlist)
        completed = sum(1 for w in non_rest if w.get("completed") == 1)
        weeks.append({
            "week_start": ws,
            "is_current": ws == today_week,
            "workouts": wlist,
            "total_km": total_km,
            "total_count": len(non_rest),
            "completed_count": completed,
        })
    return weeks


def _goal_date_range(goal: dict) -> tuple[str, str]:
    """목표의 플랜 날짜 범위 (start_iso, end_iso).

    created_at 기준 주 월요일부터 race_date+7일 또는 plan_weeks 기준 종료일.
    """
    raw_start = (goal.get("created_at") or "").split(" ")[0].split("T")[0]
    try:
        created = date.fromisoformat(raw_start)
        # 해당 주 월요일로 확장 (주 중반에 생성된 경우 앞 워크아웃 포함)
        start = (created - timedelta(days=created.weekday())).isoformat()
    except ValueError:
        start = (date.today() - timedelta(weeks=52)).isoformat()

    race = goal.get("race_date")
    if race:
        try:
            end = (date.fromisoformat(race) + timedelta(days=7)).isoformat()
            return start, end
        except ValueError:
            pass
    plan_weeks = goal.get("plan_weeks") or 12
    end = (date.fromisoformat(start) + timedelta(weeks=int(plan_weeks) + 1)).isoformat()
    return start, end


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
