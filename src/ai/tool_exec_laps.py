"""랩(세트) 단위 도구 실행기 — 랩별 기록, 세션 간 세트 비교."""
from __future__ import annotations

import sqlite3
from typing import Any

from src.ai.tool_format import columnar
from src.utils.pace import seconds_to_pace


_LAP_FIELDS = [
    ("lap", "lap_index"), ("km", "distance_m"), ("sec", "duration_sec"),
    ("pace", "avg_pace_sec_km"), ("hr", "avg_hr"), ("cad", "avg_cadence"),
    ("pwr", "avg_power"), ("type", "lap_trigger"),
]


def _lap_value(key: str, raw) -> Any:
    if raw is None:
        return None
    if key == "km":
        return round(float(raw) / 1000.0, 2)
    if key == "pace":
        return seconds_to_pace(int(raw))
    if key in ("sec", "hr", "cad", "pwr"):
        return round(float(raw))
    return raw


def _exec_get_activity_laps(conn: sqlite3.Connection, args: dict) -> dict:
    aid = args["activity_id"]
    lap_type = args.get("lap_type")

    sql = ("SELECT lap_index, distance_m, duration_sec, avg_pace_sec_km, avg_hr, "
           "avg_cadence, avg_power, lap_trigger FROM activity_laps WHERE activity_id=?")
    params: list = [aid]
    if lap_type:
        sql += " AND lap_trigger=?"
        params.append(str(lap_type).upper())
    rows = conn.execute(sql + " ORDER BY lap_index", params).fetchall()

    head = conn.execute(
        "SELECT name, date(start_time) FROM activity_summaries WHERE id=?", (aid,)
    ).fetchone()
    base: dict[str, Any] = {"activity_id": aid}
    if head:
        base["name"], base["date"] = head[0], head[1]

    if not rows:
        base["rows"] = []
        base["message"] = "랩 데이터가 없습니다 (동기화되지 않은 활동일 수 있음)"
        return base

    base.update(columnar(
        [k for k, _ in _LAP_FIELDS],
        [[_lap_value(k, r[i]) for i, (k, _) in enumerate(_LAP_FIELDS)] for r in rows],
    ))

    types: dict[str, int] = {}
    for r in rows:
        types[r[7] or "UNKNOWN"] = types.get(r[7] or "UNKNOWN", 0) + 1
    base["lap_count"] = len(rows)
    base["lap_types"] = types
    return base


def _exec_compare_workout_sets(conn: sqlite3.Connection, args: dict) -> dict:
    limit = int(args.get("limit", 5))
    sql = ("SELECT a.id, a.name, date(a.start_time) FROM v_canonical_activities a "
           "WHERE EXISTS (SELECT 1 FROM activity_laps l "
           "              WHERE l.activity_id = a.id AND l.lap_trigger = 'ACTIVE')")
    params: list = []
    if args.get("name_contains"):
        sql += " AND a.name LIKE ?"
        params.append(f"%{args['name_contains']}%")
    if args.get("start_date"):
        sql += " AND a.start_time >= ?"
        params.append(args["start_date"])
    if args.get("end_date"):
        sql += " AND a.start_time <= ? || 'T99'"
        params.append(args["end_date"])
    sql += " ORDER BY a.start_time DESC LIMIT ?"
    params.append(limit)

    sessions = []
    for aid, name, day in conn.execute(sql, params).fetchall():
        laps = conn.execute(
            "SELECT distance_m, avg_pace_sec_km, avg_hr FROM activity_laps "
            "WHERE activity_id=? AND lap_trigger='ACTIVE' ORDER BY lap_index", (aid,)
        ).fetchall()
        paces = [r[1] for r in laps if r[1]]
        hrs = [r[2] for r in laps if r[2]]
        entry: dict[str, Any] = {
            "activity_id": aid, "date": day, "name": name, "sets": len(laps),
            "work_km": round(sum(r[0] or 0 for r in laps) / 1000.0, 2),
        }
        if paces:
            entry["set_paces"] = [seconds_to_pace(int(p)) for p in paces]
            entry["avg_pace"] = seconds_to_pace(int(sum(paces) / len(paces)))
            entry["best_pace"] = seconds_to_pace(int(min(paces)))
            entry["worst_pace"] = seconds_to_pace(int(max(paces)))
            # 양수 = 마지막 세트가 첫 세트보다 느려짐(페이스 드리프트)
            entry["drift_sec"] = round(paces[-1] - paces[0])
        if hrs:
            entry["avg_hr"] = round(sum(hrs) / len(hrs))
            entry["max_set_hr"] = round(max(hrs))
        sessions.append(entry)

    if not sessions:
        return {"sessions": [],
                "message": "ACTIVE 랩이 있는 구조화 워크아웃을 찾지 못했습니다"}
    return {"count": len(sessions), "sessions": sessions}
