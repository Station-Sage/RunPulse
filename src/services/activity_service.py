"""Phase 5 서비스 레이어 - 활동 데이터 조회.

읽기 전용. DB 쓰기 없음.
첫 번째 인자는 sqlite3.Connection.
반환값은 dict/list (snake_case 키, 단위 변환 없음).

설계 문서: v0.3/data/phase-5-impl/01-service-layer.md
"""
from __future__ import annotations

import sqlite3
from collections import defaultdict
from typing import Any

from src.services.activity_impact_service import get_activity_impact
from src.utils import db_helpers
from src.utils.metric_groups import SEMANTIC_GROUPS
from src.utils.metric_registry import get_metric
from src.metrics.bands import with_grade
from src.metrics.display_rules import visible_activity_metrics
from src.utils.canonical import canonical_activity_id

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


def get_activity_detail(conn: sqlite3.Connection, activity_id: int) -> dict:
    """활동 상세: core + metrics_by_category + source_comparison + semantic_groups
    + streams + laps + best_efforts.
    """
    conn.row_factory = sqlite3.Row

    # core
    core_row = conn.execute(
        "SELECT * FROM activity_summaries WHERE id = ?", (activity_id,)
    ).fetchone()
    core = dict(core_row) if core_row else {}

    # metrics_by_category (is_primary=1)
    # RunPulse 계산값은 캐노니컬 사본에만 있다(그룹당 1회, 21 design §7.3 C3) — 사본을 열어도 같은 값을 보인다
    canonical_id = canonical_activity_id(conn, activity_id)
    primary_metrics = db_helpers.get_primary_metrics(conn, "activity", activity_id)
    if canonical_id != activity_id:
        own = {r["metric_name"] for r in primary_metrics}
        primary_metrics += [r for r in db_helpers.get_primary_metrics(conn, "activity", canonical_id)
                            if (r.get("provider") or "").startswith("runpulse") and r["metric_name"] not in own]
    primary_metrics = visible_activity_metrics(primary_metrics)
    metrics_by_category = _build_metrics_by_category(primary_metrics)

    # source_comparison (같은 matched_group의 다른 소스)
    source_comparison: dict = {}
    group_id = core.get("matched_group_id")
    if group_id:
        siblings = conn.execute(
            "SELECT * FROM activity_summaries WHERE matched_group_id = ?",
            (group_id,),
        ).fetchall()
        for row in siblings:
            row_dict = dict(row)
            source = row_dict.get("source", "unknown")
            source_comparison[source] = row_dict

    # semantic_groups (모든 provider)
    all_metrics_rows = conn.execute(
        "SELECT metric_name, provider, numeric_value, text_value, json_value, confidence"
        " FROM metric_store"
        " WHERE scope_type = 'activity' AND (scope_id = CAST(? AS TEXT)"
        "   OR (scope_id = CAST(? AS TEXT) AND provider LIKE 'runpulse%' AND ? != ?))"
        " ORDER BY metric_name, provider",
        (activity_id, canonical_id, canonical_id, activity_id),
    ).fetchall()
    all_metrics = visible_activity_metrics([dict(r) for r in all_metrics_rows])
    semantic_groups = _build_semantic_groups(all_metrics, core)

    # streams
    stream_rows = conn.execute(
        "SELECT * FROM activity_streams WHERE activity_id = ? ORDER BY elapsed_sec",
        (activity_id,),
    ).fetchall()
    streams = [dict(r) for r in stream_rows] or None

    # laps
    lap_rows = conn.execute(
        "SELECT * FROM activity_laps WHERE activity_id = ? ORDER BY lap_index",
        (activity_id,),
    ).fetchall()
    laps = [dict(r) for r in lap_rows] or None

    # best_efforts
    effort_rows = conn.execute(
        "SELECT * FROM activity_best_efforts WHERE activity_id = ? ORDER BY distance_m",
        (activity_id,),
    ).fetchall()
    best_efforts = [dict(r) for r in effort_rows] or None

    try:
        impact = get_activity_impact(conn, activity_id)
    except Exception:
        impact = None

    return {
        "core": core,
        "metrics_by_category": metrics_by_category,
        "source_comparison": source_comparison,
        "semantic_groups": semantic_groups,
        "streams": streams,
        "laps": laps,
        "best_efforts": best_efforts,
        "impact": impact,
    }


def _build_metrics_by_category(primary_metrics: list[dict]) -> dict[str, list[dict]]:
    """primary 메트릭을 category별로 그룹핑하고 registry에서 unit/description 추가."""
    grouped: dict[str, list] = defaultdict(list)
    for row in primary_metrics:
        metric_name = row["metric_name"]
        category = row.get("category") or "_unmapped"
        meta = get_metric(metric_name)
        entry = {
            "metric_name": metric_name,
            "numeric_value": row.get("numeric_value"),
            "text_value": row.get("text_value"),
            "json_value": row.get("json_value"),
            "provider": row.get("provider"),
            "confidence": row.get("confidence"),
            "unit": meta.unit if meta else "",
            "description": meta.description if meta else "",
        }
        with_grade(entry, metric_name, row.get("numeric_value"))
        grouped[category].append(entry)
    return dict(grouped)


def _build_semantic_groups(
    all_metrics: list[dict], core: dict
) -> dict[str, dict]:
    """SEMANTIC_GROUPS 기반으로 소스 비교 뷰 구성.

    metric_store에 없는 멤버는 activity_summaries 컬럼에서 fallback.
    """
    # index: (metric_name, provider) -> row
    idx: dict[tuple[str, str], dict] = {
        (r["metric_name"], r["provider"]): r for r in all_metrics
    }

    result: dict[str, dict] = {}
    for group_name, group_def in SEMANTIC_GROUPS.items():
        members: list[dict] = []
        for metric_name, provider in group_def["members"]:
            row = idx.get((metric_name, provider))
            if row:
                value = row.get("numeric_value") if row.get("numeric_value") is not None \
                    else row.get("text_value")
                members.append({
                    "metric_name": metric_name,
                    "provider": provider,
                    "value": value,
                })
            elif metric_name in core and core[metric_name] is not None:
                # activity_summaries 컬럼에서 fallback
                members.append({
                    "metric_name": metric_name,
                    "provider": provider,
                    "value": core[metric_name],
                    "source_table": "activity_summaries",
                })
        if members:
            result[group_name] = {
                "display_name": group_def["display_name"],
                "strategy": group_def.get("primary_strategy", "show_all"),
                "members": members,
            }
    return result


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
