"""planner 행 저장 단일 진입점(PLN-38) — planned_workouts 에 source='planner' 행을 넣는 유일한 경로.

v40 CHECK(source<>'planner' OR goal_id IS NOT NULL)가 goal_id 누락을 막고, 이 모듈이 goal_id 를 강제한다.
저장 시 같은 날짜의 같은 목표 planner 행만 지운다(다른 목표 행은 건드리지 않음).
"""
from __future__ import annotations

import json
import sqlite3

from .planner_config import WeekdaysRequired, resolve_run_weekdays  # noqa: F401  (단일 출처 re-export)

_STD_COLS = (
    "date", "workout_type", "distance_km", "target_pace_min", "target_pace_max", "target_hr_zone",
    "description", "rationale", "source", "interval_prescription", "structure_json",
)


def _std_values(w: dict) -> list:
    return [
        w["date"], w["workout_type"], w.get("distance_km"), w.get("target_pace_min"), w.get("target_pace_max"),
        w.get("target_hr_zone"), w.get("description"), w.get("rationale"), w.get("source", "planner"),
        w.get("interval_prescription"), json.dumps(w["structure"]) if w.get("structure") else None,
    ]


def write_planner_rows(conn: sqlite3.Connection, rows: list[dict], *, goal_id: int, restore: bool = False) -> list[int]:
    """planner 행 INSERT. goal_id 필수. restore=True 면 rows 의 모든 컬럼(id 포함)을 그대로 복원한다(replan undo).

    Returns: 새로 생긴 행 id 목록.
    """
    if goal_id is None:
        raise ValueError("goal_id 가 필요합니다 (planner 행은 목표에 속함)")
    ids: list[int] = []
    for w in rows:
        if restore:
            d = {**w, "goal_id": goal_id}
            cols = list(d)
            cur = conn.execute(
                f"INSERT INTO planned_workouts({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
                [d[c] for c in cols])
        else:
            cur = conn.execute(
                f"INSERT INTO planned_workouts({','.join(_STD_COLS)}, goal_id)"
                f" VALUES ({','.join('?' * (len(_STD_COLS) + 1))})",
                _std_values(w) + [goal_id])
        ids.append(cur.lastrowid)
    return ids


def save_weekly_plan(conn: sqlite3.Connection, plan: list[dict], commit: bool = True, *, goal_id: int) -> int:
    """주간 계획 저장 — 같은 목표의 같은 날짜 planner 행을 지우고 다시 넣는다. goal_id 필수(S4-18).

    Returns: 저장된 레코드 수.
    """
    if not plan:
        return 0
    gid = goal_id
    for w in plan:
        conn.execute("DELETE FROM planned_workouts WHERE date = ? AND source = 'planner' AND goal_id = ?",
                     (w["date"], gid))
    count = len(write_planner_rows(conn, plan, goal_id=gid))
    if commit:
        conn.commit()
    return count


def ensure_user_training_prefs(conn: sqlite3.Connection, commit: bool = True) -> None:
    """user_training_prefs 단일 행(id=1) 보장."""
    conn.execute("INSERT OR IGNORE INTO user_training_prefs (id, updated_at) VALUES (1, datetime('now'))")
    if commit:
        conn.commit()


def upsert_user_training_prefs(conn: sqlite3.Connection, rest_weekdays_mask: int = 0,
                               blocked_dates: list[str] | None = None, interval_rep_m: int = 1000,
                               max_q_days: int = 0, long_run_weekday_mask: int = 0,
                               workout_weekdays_mask: int | None = None) -> None:
    """user_training_prefs 저장. workout_weekdays_mask=None 이면 기존 값을 유지한다(미지정 상태 보존)."""
    conn.execute(
        """INSERT INTO user_training_prefs (id, rest_weekdays_mask, blocked_dates, interval_rep_m, max_q_days,
             long_run_weekday_mask, workout_weekdays_mask, updated_at)
           VALUES (1, ?, ?, ?, ?, ?, ?, datetime('now'))
           ON CONFLICT(id) DO UPDATE SET rest_weekdays_mask=excluded.rest_weekdays_mask,
             blocked_dates=excluded.blocked_dates, interval_rep_m=excluded.interval_rep_m,
             max_q_days=excluded.max_q_days, long_run_weekday_mask=excluded.long_run_weekday_mask,
             workout_weekdays_mask=COALESCE(excluded.workout_weekdays_mask, workout_weekdays_mask),
             updated_at=excluded.updated_at""",
        (rest_weekdays_mask, json.dumps(blocked_dates or [], ensure_ascii=False), interval_rep_m,
         max_q_days, long_run_weekday_mask, workout_weekdays_mask))
    conn.commit()


def set_workout_weekdays(conn: sqlite3.Connection, days, commit: bool = True) -> int:
    """운동 요일(0=월..6=일)을 마스크로 저장한다. 비어 있으면 WeekdaysRequired. 저장한 마스크를 돌려준다."""
    from .planner_config import weekdays_to_mask
    days = sorted({int(d) for d in days or []})
    if not days or any(d < 0 or d > 6 for d in days):
        raise WeekdaysRequired("운동 요일은 월~일 중 1개 이상이어야 합니다")
    mask = weekdays_to_mask(days)
    ensure_user_training_prefs(conn, commit=False)
    conn.execute("UPDATE user_training_prefs SET workout_weekdays_mask=?, updated_at=datetime('now') WHERE id=1", (mask,))
    if commit:
        conn.commit()
    return mask
