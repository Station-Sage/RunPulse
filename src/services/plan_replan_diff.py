"""재계획 미리보기용 구조 비교 — 같은 기간의 전/후 행을 종류·구조 기준으로 요약한다 (PLAN-ENGINE E2)."""
from __future__ import annotations

import sqlite3
from collections import Counter


def snapshot(conn: sqlite3.Connection, start: str, end: str) -> list[tuple]:
    """기간 내 planner 행 (date, workout_type, distance_km, has_structure)."""
    return conn.execute(
        "SELECT date, workout_type, COALESCE(distance_km, 0), structure_json IS NOT NULL"
        " FROM planned_workouts WHERE source='planner' AND date>=? AND date<=? ORDER BY date", (start, end)).fetchall()


def structure_diff(before: list[tuple], after: list[tuple]) -> dict:
    """{types: {종류: {before, after}}, structured: {before, after}, changed_days: 종류가 달라진 날 수}."""
    b, a = Counter(r[1] for r in before), Counter(r[1] for r in after)
    bt, at = {r[0]: r[1] for r in before}, {r[0]: r[1] for r in after}
    return {"types": {t: {"before": b.get(t, 0), "after": a.get(t, 0)} for t in sorted(set(b) | set(a))},
            "structured": {"before": sum(r[3] for r in before), "after": sum(r[3] for r in after)},
            "changed_days": sum(1 for d in set(bt) | set(at) if bt.get(d) != at.get(d))}
