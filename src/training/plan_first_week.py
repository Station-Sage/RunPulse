"""시작 주(부분 주) 보정 — PLN-32 a · PLN-45 b-lite.

주는 월요일 기준을 유지하고, 시작일이 주중이면 남은 요일만 계획한다(그 주가 1주차).
주간 볼륨 목표는 남은 일수 비율로 줄이고, 이번 주에 이미 뛴 같은 유형의 품질·롱런은 남은 요일에서 이지로 바꾼다.
이미 뛴 거리는 목표에서 빼지 않는다. 같은 날 두 번째 활동은 날짜 키 때문에 분류에서 빠질 수 있다(알려진 한계).
"""
from __future__ import annotations

import sqlite3
from datetime import date

from src.training.plan_structure import structure_for_plan
from src.training.week_compliance import QUALITY_TYPES, RUN_TYPES

_SKIP = ("rest", "race")


def classes_run_between(conn: sqlite3.Connection, start: str, end: str) -> set[str]:
    """[start, end] 에 달린 활동의 분류 태그(metric_store workout_type_classified). 분류 없는 활동은 제외."""
    marks = ",".join("?" * len(RUN_TYPES))
    rows = conn.execute(
        f"SELECT DISTINCT m.text_value FROM v_canonical_activities a JOIN metric_store m"
        f" ON m.scope_type='activity' AND m.scope_id = CAST(a.id AS TEXT) AND m.metric_name='workout_type_classified'"
        f" WHERE a.activity_type IN ({marks}) AND substr(a.start_time, 1, 10) BETWEEN ? AND ?"
        f" AND m.text_value IS NOT NULL", (*RUN_TYPES, start, end)).fetchall()
    return {r[0] for r in rows}


def trim_first_week(conn: sqlite3.Connection, plan: list[dict], today: date) -> list[dict]:
    """오늘 이전 행을 빼고, 남은 일수 비율로 거리를 줄이며, 이미 한 품질·롱 유형은 이지로 바꾼다."""
    if not plan:
        return plan
    week_start = date.fromisoformat(plan[0]["date"])
    full_km = sum(r["distance_km"] or 0 for r in plan if r["workout_type"] not in _SKIP)
    kept = [r for r in plan if r["date"] >= today.isoformat()]
    if len(kept) == len(plan):
        return kept
    done = classes_run_between(conn, week_start.isoformat(), today.isoformat()) if today > week_start else set()
    avoid = {t for t in done if t in QUALITY_TYPES or t == "long"}
    for r in kept:
        if r["workout_type"] in avoid:
            r["workout_type"] = "easy"
            r["description"] = f"easy {r['distance_km'] or 0:.1f}km"
            r["rationale"] = "이번 주 이미 같은 유형을 수행해 이지로 대체"
            r["structure"] = None
            r["interval_prescription"] = None
    runs = [r for r in kept if r["workout_type"] not in _SKIP]
    cur = sum(r["distance_km"] or 0 for r in runs)
    target = round(full_km * len(kept) / 7, 1)
    if runs and cur > 0 and target > 0:
        k = target / cur
        for r in runs:
            r["distance_km"] = round((r["distance_km"] or 0) * k, 1)
            r["description"] = _redescribe(r)
            r["structure"] = structure_for_plan(r["workout_type"], r["distance_km"], r.get("target_pace_min"),
                                                r.get("target_pace_max"), r.get("interval_prescription"))
    return kept


def _redescribe(r: dict) -> str:
    desc = r.get("description") or ""
    head = desc.split(" ")[0] if desc else r["workout_type"]
    return f"{head} {r['distance_km']:.1f}km"
