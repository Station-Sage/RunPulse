"""활동 단위 도구 실행기 — 요약, 기간 목록, 상세, 랩, 세트 비교."""
from __future__ import annotations

import sqlite3
from datetime import date
from typing import Any

from src.ai.tool_format import (
    DEFAULT_WEEK_START, WEEKLY_ACTIVITY_FIELDS, columnar, num,
    resolve_granularity, span_days, weekly_activity_rows,
)
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
            "SELECT text_value FROM metric_store "
            "WHERE metric_name='workout_type_classified' AND scope_type='activity' AND scope_id=CAST(? AS TEXT)",
            (aid,),
        ).fetchone()
        if cls and cls[0]:
            detail["workout_type"] = cls[0]
        result.append(detail)
    return {"date": d, "activities": result}


def _exec_get_activities_range(conn: sqlite3.Connection, args: dict) -> dict:
    s, e = args["start_date"], args["end_date"]
    first = args.get("week_start", DEFAULT_WEEK_START)
    gran, note = resolve_granularity(args.get("granularity"), span_days(s, e))
    rows = conn.execute(
        "SELECT date(start_time), distance_m / 1000.0 AS distance_km, duration_sec, avg_pace_sec_km, "
        "avg_hr, name, id FROM v_canonical_activities "
        "WHERE activity_type='running' AND start_time>=? AND start_time<=? || 'T99' "
        "ORDER BY start_time", (s, e),
    ).fetchall()
    out: dict[str, Any] = {"period": f"{s} ~ {e}", "count": len(rows), "granularity": gran}
    if note:
        out["note"] = note
    if gran == "week":
        out["unit"] = f"week({'Mon' if first == 'mon' else 'Sun'}-start)"
        out.update(columnar(WEEKLY_ACTIVITY_FIELDS, weekly_activity_rows(
            [(r[0], r[1], r[2], r[4]) for r in rows], first, (s, e))))
        return out
    out.update(columnar(
        ["id", "date", "km", "min", "pace", "hr", "name"],
        [[r[6], r[0], num(r[1], 2) if r[1] else None,
          num(r[2] / 60, 1) if r[2] else None,
          seconds_to_pace(int(r[3])) if r[3] else None,
          num(r[4]), r[5]] for r in rows],
    ))
    return out


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
