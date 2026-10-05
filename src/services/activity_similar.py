"""활동 상세 '비슷한 활동' 비교 — 같은 코스 → 같은 유형 → 비슷한 거리 순으로 기준을 고른다.

읽기 전용. 기준별 표본이 SIMILAR_MIN_N 미만이면 다음 기준으로 내려가고, 모두 부족하면 None.
유형은 metric_store의 workout_type_classified(분류기 결과)를 그대로 읽는다(재분류 금지).
기간 제한 없이 전체 이력을 쓴다(D-3).
"""
from __future__ import annotations

import math
import sqlite3
from statistics import median

from src.services.activity_list_filters import TYPE_CLASSES
from src.metrics.workout_classifier import TAG_LABELS
from src.utils.activity_types import normalize_activity_type

SIMILAR_MIN_N = 5
DISTANCE_BAND = 0.15
COURSE_START_RADIUS_M = 300.0
COURSE_DISTANCE_BAND = 0.10
_CLASS_TO_KEY = {v: k for k, vals in TYPE_CLASSES.items() for v in vals}


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = (math.sin((p2 - p1) / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2)
    return 12742000.0 * math.asin(math.sqrt(a))


def _metric_map(conn: sqlite3.Connection, ids: list[int], metric: str, col: str) -> dict[int, object]:
    out: dict[int, object] = {}
    for i in range(0, len(ids), 500):
        chunk = [str(x) for x in ids[i:i + 500]]
        q = ",".join("?" * len(chunk))
        for sid, val in conn.execute(
            f"SELECT scope_id, {col} FROM metric_store WHERE scope_type='activity' AND metric_name=?"
            f" AND provider LIKE 'runpulse%' AND {col} IS NOT NULL AND scope_id IN ({q}) ORDER BY is_primary",
            (metric, *chunk),
        ):
            out[int(sid)] = val
    return out


def _candidates(conn: sqlite3.Connection, start_time: str) -> list[dict]:
    rows = conn.execute(
        "SELECT v.id, v.activity_type, v.source, v.distance_m, v.avg_pace_sec_km, a.start_lat, a.start_lon"
        " FROM v_canonical_activities v JOIN activity_summaries a ON a.id = v.id"
        " WHERE v.start_time < ? AND v.distance_m > 0 AND v.avg_pace_sec_km IS NOT NULL"
        " ORDER BY v.start_time DESC", (start_time,)).fetchall()
    return [dict(r) for r in rows
            if normalize_activity_type(r["activity_type"], r["source"]) == "running"]


def _summary(basis: str, pool: list[dict], pace: float, load: float | None, **extra) -> dict:
    paces = [c["avg_pace_sec_km"] for c in pool]
    avg = round(sum(paces) / len(paces), 1)
    loads = [c["load"] for c in pool if c.get("load") is not None]
    med = round(median(loads), 1) if loads else None
    pct = round((load - med) / med * 100, 1) if load is not None and med else None
    return {"basis": basis, "n": len(pool), "pace_rank": sum(1 for p in paces if p < pace) + 1,
            "avg_pace_sec_km": avg, "pace_diff_sec": round(pace - avg, 1),
            "load_median": med, "load_pct_vs_median": pct, **extra}


def find_similar(conn: sqlite3.Connection, activity_id: int, start_time: str, distance_m: float,
                 pace: float | None, start_lat: float | None, start_lon: float | None) -> dict | None:
    """같은 코스 → 같은 유형 → 비슷한 거리 순서로 첫 충분한 기준의 비교 요약. 없으면 None."""
    if pace is None:
        return None
    cands = [c for c in _candidates(conn, start_time) if c["id"] != activity_id]
    ids = [c["id"] for c in cands] + [activity_id]
    classes = _metric_map(conn, ids, "workout_type_classified", "text_value")
    loads = _metric_map(conn, ids, "hrss", "numeric_value")
    for c in cands:
        c["cls"] = _CLASS_TO_KEY.get(classes.get(c["id"]))
        c["load"] = float(loads[c["id"]]) if c["id"] in loads else None
    my_cls = _CLASS_TO_KEY.get(classes.get(activity_id))
    my_load = float(loads[activity_id]) if activity_id in loads else None

    if start_lat is not None and start_lon is not None:
        course = [c for c in cands if c["start_lat"] is not None and c["start_lon"] is not None
                  and abs(c["distance_m"] - distance_m) <= distance_m * COURSE_DISTANCE_BAND
                  and _haversine_m(start_lat, start_lon, c["start_lat"], c["start_lon"]) <= COURSE_START_RADIUS_M]
        if len(course) >= SIMILAR_MIN_N:
            return _summary("same_course", course, pace, my_load)
    if my_cls:
        same = [c for c in cands if c["cls"] == my_cls]
        if len(same) >= SIMILAR_MIN_N:
            return _summary("same_class", same, pace, my_load, workout_class=my_cls,
                            class_label=TAG_LABELS.get(my_cls, my_cls))
    near = [c for c in cands if abs(c["distance_m"] - distance_m) <= distance_m * DISTANCE_BAND]
    if len(near) >= SIMILAR_MIN_N:
        return _summary("distance", near, pace, my_load)
    return None
