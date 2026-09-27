"""주간 planned_workouts 조회(결과·대체됨 플래그 포함) — planner.py 에서 분리."""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta


def get_planned_workouts(
    conn: sqlite3.Connection,
    week_start: date | None = None,
) -> list[dict]:
    """이번 주 (또는 지정 주) planned_workouts 조회."""
    if week_start is None:
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=7)

    rows = conn.execute(
        """SELECT p.id, p.date, p.workout_type, p.distance_km, p.target_pace_min, p.target_pace_max,
                  p.target_hr_zone, p.description, p.rationale, p.completed, p.source, p.ai_model,
                  p.interval_prescription, p.matched_activity_id, o.outcome_label, o.dist_ratio,
                  o.actual_dist_km
           FROM planned_workouts p LEFT JOIN session_outcomes o ON o.planned_id = p.id
           WHERE p.date >= ? AND p.date < ?
           ORDER BY p.date, (p.source = 'planner') DESC""",
        (week_start.isoformat(), week_end.isoformat()),
    ).fetchall()

    keys = ["id", "date", "workout_type", "distance_km", "target_pace_min",
            "target_pace_max", "target_hr_zone", "description", "rationale",
            "completed", "source", "ai_model", "interval_prescription",
            "matched_activity_id", "outcome_label", "dist_ratio", "actual_dist_km"]
    out = [dict(zip(keys, r)) for r in rows]
    # 같은 날 다른 계획(Garmin 저장 워크아웃 등)이 실제 활동을 가져갔으면 추천안(planner)은 '대체됨'
    taken = {w["date"] for w in out if w["source"] != "planner" and w["matched_activity_id"]}
    for w in out:
        w["superseded"] = w["source"] == "planner" and not w["completed"] and w["date"] in taken
    return out
