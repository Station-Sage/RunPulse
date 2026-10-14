"""기간 러닝 합계·비러닝 요약 단일 출처 (ADR-051 NRA-1/NRA-2).

주간·월간·Story 가 같은 규칙으로 러닝만 집계하게 한다. 비러닝은 `other_totals` 로 따로 센다.
"""
from __future__ import annotations

import sqlite3

from src.utils.activity_types import FAMILIES, SPORT_LABELS, family_clause

_RANGE = "DATE(start_time) >= ? AND DATE(start_time) <= ?"


def run_totals(conn: sqlite3.Connection, start: str, end: str) -> dict:
    """[start, end] 러닝 횟수·거리(km)·최장(km). 데이터 없으면 0."""
    clause, params = family_clause("running")
    row = conn.execute(
        "SELECT COUNT(*), COALESCE(SUM(distance_m), 0), COALESCE(MAX(distance_m), 0)"
        f" FROM v_canonical_activities WHERE {_RANGE} AND {clause}",
        (start, end, *params),
    ).fetchone()
    count = int(row[0]) if row else 0
    return {
        "count": count,
        "distance_km": round(float(row[1] or 0) / 1000.0, 1) if count else 0.0,
        "longest_km": round(float(row[2] or 0) / 1000.0, 1) if count else 0.0,
    }


def other_totals(conn: sqlite3.Connection, start: str, end: str) -> list[dict]:
    """[start, end] 비러닝 활동을 스포츠 군별로 집계. 러닝 제외, 횟수 내림차순."""
    from src.utils.activity_types import sport_family

    rows = conn.execute(
        "SELECT activity_type, source, COALESCE(distance_m, 0), COALESCE(duration_sec, 0)"
        f" FROM v_canonical_activities WHERE {_RANGE}",
        (start, end),
    ).fetchall()
    agg: dict[str, dict] = {}
    for atype, source, dist, dur in rows:
        fam = sport_family(atype, source)
        if fam == "running":
            continue
        a = agg.setdefault(fam, {"family": fam, "count": 0, "dist": 0.0, "dur": 0.0})
        a["count"] += 1
        a["dist"] += float(dist)
        a["dur"] += float(dur)
    order = {f: i for i, f in enumerate(FAMILIES)}
    out = [
        {"family": f, "label": SPORT_LABELS.get(f, "기타"), "count": a["count"],
         "distance_km": round(a["dist"] / 1000.0, 1), "duration_sec": int(a["dur"])}
        for f, a in agg.items()
    ]
    out.sort(key=lambda d: (-d["count"], order.get(d["family"], 99)))
    return out


def other_line(others: list[dict]) -> str:
    """"그 외 수영 1회 · 근력 2회" — 비러닝이 없으면 빈 문자열."""
    if not others:
        return ""
    return "그 외 " + " · ".join(f"{o['label']} {o['count']}회" for o in others)
