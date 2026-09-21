"""활동 단위 도구 실행기 — 요약, 기간 목록, 상세, 랩, 세트 비교."""
from __future__ import annotations

import sqlite3
from datetime import date
from typing import Any

from src.utils.pace import seconds_to_pace


def _exec_get_activity(conn: sqlite3.Connection, args: dict) -> dict:
    d = args.get("date", date.today().isoformat())
    acts = conn.execute(
        "SELECT id, distance_m / 1000.0 AS distance_km, duration_sec, avg_pace_sec_km, avg_hr, max_hr, "
        "elevation_gain, name FROM v_canonical_activities "
        "WHERE activity_type='running' AND date(start_time)=? ORDER BY start_time",
        (d,),
    ).fetchall()
    if not acts:
        return {"date": d, "activities": [], "message": "해당 날짜에 활동이 없습니다"}

    result = []
    for a in acts:
        aid, km, sec, pace, avg_hr, max_hr, elev, name = a
        detail: dict[str, Any] = {
            "activity_id": aid,
            "name": name,
            "distance_km": round(float(km), 2) if km else None,
            "duration_sec": round(float(sec)) if sec else None,
            "pace": seconds_to_pace(int(pace)) if pace else None,
            "avg_hr": round(float(avg_hr)) if avg_hr else None,
            "max_hr": round(float(max_hr)) if max_hr else None,
            "elevation_m": round(float(elev)) if elev else None,
        }
        # 메트릭
        metrics = conn.execute(
            "SELECT metric_name, numeric_value FROM metric_store "
            "WHERE scope_type='activity' AND scope_id=CAST(? AS TEXT) AND numeric_value IS NOT NULL",
            (aid,),
        ).fetchall()
        detail["metrics"] = {r[0]: round(float(r[1]), 2) for r in metrics}
        # 분류
        cls = conn.execute(
            "SELECT numeric_value FROM metric_store "
            "WHERE metric_name='workout_type_classified' AND scope_type='activity' AND scope_id=CAST(? AS TEXT)",
            (aid,),
        ).fetchone()
        if cls:
            detail["workout_type"] = cls[0]
        result.append(detail)
    return {"date": d, "activities": result}


def _exec_get_activities_range(conn: sqlite3.Connection, args: dict) -> dict:
    s, e = args["start_date"], args["end_date"]
    rows = conn.execute(
        "SELECT date(start_time), distance_m / 1000.0 AS distance_km, duration_sec, avg_pace_sec_km, "
        "avg_hr, name, id FROM v_canonical_activities "
        "WHERE activity_type='running' AND start_time>=? AND start_time<=? || 'T99' "
        "ORDER BY start_time", (s, e),
    ).fetchall()
    return {
        "period": f"{s} ~ {e}",
        "count": len(rows),
        "activities": [
            {"activity_id": r[6], "date": r[0],
             "km": round(float(r[1]), 2) if r[1] else None,
             "sec": round(float(r[2])) if r[2] else None,
             "pace": seconds_to_pace(int(r[3])) if r[3] else None,
             "hr": round(float(r[4])) if r[4] else None, "name": r[5]}
            for r in rows
        ],
    }


def _exec_get_activity_detail(conn: sqlite3.Connection, args: dict) -> dict:
    import json as _json
    import math as _math
    aid = args["activity_id"]

    # laps
    laps_raw = conn.execute(
        "SELECT lap_index, distance_m / 1000.0 AS distance_km, duration_sec, avg_pace_sec_km, avg_hr "
        "FROM activity_laps WHERE activity_id=? ORDER BY lap_index", (aid,)
    ).fetchall()
    laps = [
        {"lap": r[0], "km": round(r[1], 2), "sec": r[2],
         "pace": f"{int(r[3]//60)}:{int(r[3]%60):02d}" if r[3] else None,
         "hr": r[4]}
        for r in laps_raw
    ]

    # streams
    from src.utils.db_helpers import load_activity_streams
    streams = load_activity_streams(conn, aid)

    latlng = streams.get("latlng", [])
    lat_s = [p[0] for p in latlng]
    lon_s = [p[1] for p in latlng]
    hr = streams.get("heartrate", [])
    cad = streams.get("cadence", [])
    pwr = streams.get("watts", [])

    def _haversine(lat1, lon1, lat2, lon2):
        R = 6371000
        p = _math.pi / 180
        a = (_math.sin((lat2 - lat1) * p / 2) ** 2
             + _math.cos(lat1 * p) * _math.cos(lat2 * p)
             * _math.sin((lon2 - lon1) * p / 2) ** 2)
        return 2 * R * _math.asin(_math.sqrt(a))

    # km splits (latlng 기반 거리 + time 스트림 기반 시간)
    km_splits: list[dict] = []
    if lat_s and lon_s and len(lat_s) == len(lon_s):
        time_s = streams.get("time", [])
        # time 스트림 없으면 총시간으로 균등 근사
        act_row = conn.execute(
            "SELECT duration_sec FROM activity_summaries WHERE id=?", (aid,)
        ).fetchone()
        total_sec = act_row[0] if act_row else len(lat_s)
        total_pts = len(lat_s)

        dist_acc = 0.0
        seg_start = 0
        for i in range(1, len(lat_s)):
            dist_acc += _haversine(lat_s[i-1], lon_s[i-1], lat_s[i], lon_s[i])
            if dist_acc >= 1000:
                n = i - seg_start + 1
                if time_s and len(time_s) > i:
                    seg_sec = time_s[i] - (time_s[seg_start] if seg_start < len(time_s) else 0)
                else:
                    seg_sec = total_sec / total_pts * n
                pace_s = seg_sec / (dist_acc / 1000) if dist_acc > 0 else 0

                split: dict = {
                    "km": len(km_splits) + 1,
                    "pace": f"{int(pace_s//60)}:{int(pace_s%60):02d}" if pace_s else None,
                }
                if hr and len(hr) > i:
                    seg_hr = hr[seg_start:i+1]
                    if seg_hr:
                        split["avg_hr"] = round(sum(seg_hr) / len(seg_hr))
                if cad and len(cad) > i:
                    seg_cad = cad[seg_start:i+1]
                    if seg_cad:
                        split["cadence"] = round(sum(seg_cad) / len(seg_cad))
                if pwr and len(pwr) > i:
                    seg_pwr = pwr[seg_start:i+1]
                    if seg_pwr:
                        split["power"] = round(sum(seg_pwr) / len(seg_pwr))
                km_splits.append(split)
                dist_acc -= 1000
                seg_start = i + 1

    # HR zones
    hr_zones: dict = {}
    if hr:
        total = len(hr)
        for name, lo, hi in [
            ("z1_<120", 0, 120), ("z2_120-140", 120, 140),
            ("z3_140-160", 140, 160), ("z4_160-180", 160, 180),
            ("z5_180+", 180, 999),
        ]:
            cnt = sum(1 for h in hr if lo <= h < hi)
            hr_zones[name] = f"{round(cnt / total * 100)}%"

    avg_power = round(sum(pwr) / len(pwr)) if pwr else None

    return {
        "activity_id": aid,
        "laps": laps,
        "km_splits": km_splits,
        "hr_zones": hr_zones,
        "avg_power": avg_power,
    }


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
        base["laps"] = []
        base["message"] = "랩 데이터가 없습니다 (동기화되지 않은 활동일 수 있음)"
        return base

    values = [[_lap_value(k, r[i]) for i, (k, _) in enumerate(_LAP_FIELDS)] for r in rows]
    keep = [i for i in range(len(_LAP_FIELDS))
            if any(v[i] is not None for v in values)]
    base["fields"] = [_LAP_FIELDS[i][0] for i in keep]
    base["laps"] = [[v[i] for i in keep] for v in values]

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
