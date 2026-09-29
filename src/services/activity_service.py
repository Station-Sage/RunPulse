"""Phase 5 서비스 레이어 - 활동 데이터 조회.

읽기 전용. DB 쓰기 없음.
첫 번째 인자는 sqlite3.Connection.
반환값은 dict/list (snake_case 키, 단위 변환 없음).

설계 문서: v0.3/data/phase-5-impl/01-service-layer.md
"""
from __future__ import annotations

import sqlite3
from typing import Any

# get_activity_detail은 300줄 규칙 위반으로 activity_detail_service.py로 분리(re-export shim).
from src.services.activity_detail_service import get_activity_detail  # noqa: F401

SERVICE_PRIORITY = ["garmin", "strava", "intervals", "runalyze"]

SOURCE_COLORS: dict[str, str] = {
    "garmin": "#0055b3",
    "strava": "#FC4C02",
    "intervals": "#00884e",
    "runalyze": "#7b2d8b",
}

_ALLOWED_SORT = {
    "start_time", "distance_m", "duration_sec", "avg_hr",
    "avg_pace_sec_km", "elevation_gain",
}


def get_activity_list(
    conn: sqlite3.Connection,
    filters: dict | None = None,
    sort_by: str = "start_time",
    sort_dir: str = "DESC",
    page: int = 1,
    per_page: int = 20,
) -> dict:
    """v_canonical_activities에서 필터/정렬/페이징.

    filters 키: activity_type, date_from, date_to, min_distance_m, search
    """
    if sort_by not in _ALLOWED_SORT:
        sort_by = "start_time"
    sort_dir = "DESC" if sort_dir.upper() != "ASC" else "ASC"

    filters = filters or {}
    clauses: list[str] = []
    params: list[Any] = []

    if filters.get("activity_type"):
        clauses.append("activity_type = ?")
        params.append(filters["activity_type"])
    if filters.get("date_from"):
        clauses.append("start_time >= ?")
        params.append(filters["date_from"])
    if filters.get("date_to"):
        clauses.append("start_time <= ?")
        params.append(filters["date_to"])
    if filters.get("min_distance_m") is not None:
        clauses.append("distance_m >= ?")
        params.append(filters["min_distance_m"])
    if filters.get("search"):
        clauses.append("name LIKE ?")
        params.append(f"%{filters['search']}%")

    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""

    conn.row_factory = sqlite3.Row
    total_row = conn.execute(
        f"SELECT COUNT(*) FROM v_canonical_activities{where}", params
    ).fetchone()
    total = total_row[0] if total_row else 0

    offset = (page - 1) * per_page
    rows = conn.execute(
        f"SELECT * FROM v_canonical_activities{where}"
        f" ORDER BY {sort_by} {sort_dir} LIMIT ? OFFSET ?",
        params + [per_page, offset],
    ).fetchall()

    activities = [dict(r) for r in rows]
    previews = _route_previews(conn, [a["id"] for a in activities])
    for a in activities:
        a["route"] = previews.get(a["id"])

    return {
        "activities": activities,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": max(1, (total + per_page - 1) // per_page),
    }


_ROUTE_PREVIEW_POINTS = 32
_ROUTE_PREVIEW_MAX_ACTIVITIES = 50


def _route_previews(conn: sqlite3.Connection, ids: list[int]) -> dict[int, list[list[float]]]:
    """활동별 GPS 경로 미리보기 — 균등 간격 ≤32점의 [lat, lng]. GPS 없는 활동은 결과에서 빠진다.

    목록 썸네일용이라 활동당 전체 스트림을 내려주지 않는다. 한 번에 50개 초과 활동은 건너뛴다.
    """
    if not ids or len(ids) > _ROUTE_PREVIEW_MAX_ACTIVITIES:
        return {}
    marks = ",".join("?" * len(ids))
    rows = conn.execute(
        f"SELECT activity_id, latitude, longitude FROM activity_streams"
        f" WHERE activity_id IN ({marks}) AND latitude IS NOT NULL AND longitude IS NOT NULL"
        f" ORDER BY activity_id, elapsed_sec",
        ids,
    ).fetchall()
    by_act: dict[int, list[list[float]]] = {}
    for r in rows:
        by_act.setdefault(r[0], []).append([r[1], r[2]])
    out: dict[int, list[list[float]]] = {}
    for aid, pts in by_act.items():
        if len(pts) < 2:
            continue
        n = _ROUTE_PREVIEW_POINTS
        picked = pts if len(pts) <= n else [pts[round(i * (len(pts) - 1) / (n - 1))] for i in range(n)]
        out[aid] = [[round(la, 5), round(lo, 5)] for la, lo in picked]
    return out


def get_activity_streams(
    conn: sqlite3.Connection,
    activity_id: int,
    source: str | None = None,
) -> list[dict]:
    """활동 스트림 데이터 (elapsed_sec 순)."""
    conn.row_factory = sqlite3.Row
    if source:
        rows = conn.execute(
            "SELECT * FROM activity_streams"
            " WHERE activity_id = ? AND source = ? ORDER BY elapsed_sec",
            (activity_id, source),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM activity_streams"
            " WHERE activity_id = ? ORDER BY elapsed_sec",
            (activity_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_activity_trend(
    conn: sqlite3.Connection,
    metric_name: str,
    days: int = 90,
    activity_type: str | None = None,
) -> list[dict]:
    """메트릭의 날짜별 시계열. [{"date", "value", "activity_id"}, ...]"""
    conn.row_factory = sqlite3.Row
    date_expr = f"-{days} days"
    clauses = [
        "m.scope_type = 'activity'",
        "m.metric_name = ?",
        "m.is_primary = 1",
        "a.start_time >= date('now','localtime', ?)",
    ]
    params: list[Any] = [metric_name, date_expr]

    if activity_type:
        clauses.append("a.activity_type = ?")
        params.append(activity_type)

    where = " AND ".join(clauses)
    rows = conn.execute(
        f"SELECT substr(a.start_time, 1, 10) AS date,"
        f"       m.numeric_value AS value,"
        f"       a.id AS activity_id"
        f" FROM metric_store m"
        f" JOIN v_canonical_activities a ON CAST(m.scope_id AS INTEGER) = a.id"
        f" WHERE {where}"
        f" ORDER BY a.start_time",
        params,
    ).fetchall()
    return [dict(r) for r in rows]
