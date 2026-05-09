"""멀티 소스 활동 통합 뷰 — UnifiedActivity 빌드 + 페이지 조회.

unified_activities.py의 멀티소스 병합 로직을 서비스 레이어로 분리.
상수/우선순위는 activity_service에서 import.
그룹 관리 함수(assign/remove)는 utils.dedup에서 import.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from typing import Any

from src.services.activity_service import SERVICE_PRIORITY, SOURCE_COLORS  # noqa: F401

_COLS = [
    "id", "source", "source_id", "name", "activity_type", "start_time",
    "distance_m", "duration_sec", "avg_pace_sec_km", "avg_hr",
    "max_hr", "avg_cadence", "elevation_gain",
    "description", "matched_group_id", "workout_label", "avg_power",
    "event_type",
]


@dataclass
class UnifiedField:
    """단일 필드의 통합 값 + 출처 정보."""
    value: Any = None
    source: str | None = None
    all_values: dict[str, Any] = field(default_factory=dict)


@dataclass
class UnifiedActivity:
    """멀티 소스 활동을 통합한 뷰 모델."""
    effective_group_id: str
    is_real_group: bool
    representative_id: int
    available_sources: list[str]
    source_rows: dict[str, dict]  # source → row dict

    activity_type: UnifiedField = field(default_factory=UnifiedField)
    start_time: UnifiedField = field(default_factory=UnifiedField)
    distance_m: UnifiedField = field(default_factory=UnifiedField)
    duration_sec: UnifiedField = field(default_factory=UnifiedField)
    avg_pace_sec_km: UnifiedField = field(default_factory=UnifiedField)
    avg_hr: UnifiedField = field(default_factory=UnifiedField)
    max_hr: UnifiedField = field(default_factory=UnifiedField)
    avg_cadence: UnifiedField = field(default_factory=UnifiedField)
    elevation_gain: UnifiedField = field(default_factory=UnifiedField)
    name: UnifiedField = field(default_factory=UnifiedField)
    description: UnifiedField = field(default_factory=UnifiedField)
    workout_label: UnifiedField = field(default_factory=UnifiedField)
    event_type: UnifiedField = field(default_factory=UnifiedField)

    @property
    def date(self) -> str:
        st = self.start_time.value
        s = str(st)
        if len(s) >= 16:
            return s[:10] + " " + s[11:16]
        return s[:10] if len(s) >= 10 else (s or "—")

    @property
    def can_expand(self) -> bool:
        return self.is_real_group or len(self.available_sources) > 1


def _pick_value(source_rows: dict[str, dict], field_name: str) -> UnifiedField:
    """Garmin 우선 순서로 non-None 값 선택."""
    all_values: dict[str, Any] = {}
    for src, row in source_rows.items():
        v = row.get(field_name)
        if v is not None:
            all_values[src] = v

    for src in SERVICE_PRIORITY:
        if src in all_values:
            return UnifiedField(value=all_values[src], source=src, all_values=all_values)

    for src, v in all_values.items():
        return UnifiedField(value=v, source=src, all_values=all_values)

    return UnifiedField(value=None, source=None, all_values={})


def build_unified_activity(group_id: str | None, rows: list[dict], **kwargs) -> UnifiedActivity:
    """row 목록(같은 그룹)으로 UnifiedActivity 생성.

    Args:
        group_id: matched_group_id. None이면 단일 소스 활동.
        rows: activity_summaries 행 dict 리스트.
    """
    is_real_group = group_id is not None
    source_rows: dict[str, dict] = {}
    for row in rows:
        src = row["source"]
        if src not in source_rows:
            source_rows[src] = row

    rep_id = rows[0]["id"]
    for src in SERVICE_PRIORITY:
        if src in source_rows:
            rep_id = source_rows[src]["id"]
            break

    available_sources = sorted(
        source_rows.keys(),
        key=lambda s: SERVICE_PRIORITY.index(s) if s in SERVICE_PRIORITY else 99,
    )

    eff_gid = group_id if group_id else str(rows[0]["id"])

    ua = UnifiedActivity(
        effective_group_id=eff_gid,
        is_real_group=is_real_group,
        representative_id=rep_id,
        available_sources=available_sources,
        source_rows=source_rows,
    )
    for fname in [
        "activity_type", "start_time", "distance_m", "duration_sec",
        "avg_pace_sec_km", "avg_hr", "max_hr", "avg_cadence",
        "elevation_gain", "name", "description", "workout_label",
        "event_type",
    ]:
        setattr(ua, fname, _pick_value(source_rows, fname))

    try:
        import json as _json
        wt_data = None
        if "_wt_cache" in kwargs:
            wt_data = kwargs["_wt_cache"].get(rep_id)
        if wt_data:
            source_rows["_rp_workout_type"] = wt_data
    except Exception:
        pass

    return ua


def fetch_unified_activities(
    conn: sqlite3.Connection,
    source_filter: str = "",
    act_type_filter: str = "",
    date_from: str = "",
    date_to: str = "",
    page: int = 1,
    page_size: int = 20,
    sort_by: str = "date",
    sort_dir: str = "desc",
    q: str = "",
    min_dist: float | None = None,
    max_dist: float | None = None,
    min_pace: int | None = None,
    max_pace: int | None = None,
    min_dur: int | None = None,
    max_dur: int | None = None,
) -> tuple[list[UnifiedActivity], int, dict]:
    """필터·페이지를 적용하여 통합 활동 목록 반환.

    Returns:
        (activities, total_count, stats)
        stats: {total_count, total_dist_km}
    """
    conditions = []
    params: list = []

    _TYPE_GROUPS: dict[str, list[str]] = {
        "running":  ["running", "run", "virtualrun", "treadmill", "treadmill_running",
                     "track_running", "trail_running"],
        "swimming": ["swimming", "open_water_swimming"],
        "strength": ["strength", "hiit", "highintensityintervaltraining", "workout",
                     "elliptical", "yoga"],
        "hiking":   ["hiking", "walking"],
    }

    if source_filter and source_filter in ["garmin", "strava", "intervals", "runalyze"]:
        conditions.append("source = ?")
        params.append(source_filter)

    if act_type_filter and act_type_filter in _TYPE_GROUPS:
        types = _TYPE_GROUPS[act_type_filter]
        placeholders = ",".join("?" * len(types))
        conditions.append(f"activity_type IN ({placeholders})")
        params.extend(types)

    if date_from:
        conditions.append("start_time >= ?")
        params.append(date_from)

    if date_to:
        conditions.append("start_time <= ?")
        params.append(date_to + "T99")

    if q:
        conditions.append("(description LIKE ? OR activity_type LIKE ?)")
        like = f"%{q}%"
        params.extend([like, like])

    if min_dist is not None:
        conditions.append("distance_m >= ?")
        params.append(min_dist * 1000)

    if max_dist is not None:
        conditions.append("distance_m <= ?")
        params.append(max_dist * 1000)

    if min_pace is not None:
        conditions.append("avg_pace_sec_km >= ?")
        params.append(min_pace)

    if max_pace is not None:
        conditions.append("avg_pace_sec_km <= ?")
        params.append(max_pace)

    if min_dur is not None:
        conditions.append("duration_sec >= ?")
        params.append(min_dur)

    if max_dur is not None:
        conditions.append("duration_sec <= ?")
        params.append(max_dur)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    _DB_SORT_COL: dict[str, str] = {
        "date":     "MAX(start_time)",
        "distance": "MAX(distance_m)",
        "duration": "MAX(duration_sec)",
        "pace":     "MIN(CASE WHEN avg_pace_sec_km > 0 THEN avg_pace_sec_km END)",
        "hr":       "MAX(avg_hr)",
    }
    sort_col = _DB_SORT_COL.get(sort_by, "MAX(start_time)")
    order = "ASC" if sort_dir == "asc" else "DESC"

    # Step 1: 전체 그룹 수 + 통계
    stats_sql = f"""
        SELECT
            COUNT(*),
            COALESCE(SUM(rep_dist), 0)
        FROM (
            SELECT MAX(distance_m) / 1000.0 AS rep_dist
            FROM activity_summaries
            {where}
            GROUP BY COALESCE(matched_group_id, CAST(id AS TEXT))
        )
    """
    stats_row = conn.execute(stats_sql, params).fetchone()
    total_count = stats_row[0] if stats_row else 0
    total_dist = float(stats_row[1]) if stats_row else 0.0

    # Step 2: 현재 페이지 eff_gid 목록
    offset = (page - 1) * page_size
    page_sql = f"""
        SELECT COALESCE(matched_group_id, CAST(id AS TEXT)) AS eff_gid,
               MAX(matched_group_id IS NOT NULL) AS is_group
        FROM activity_summaries
        {where}
        GROUP BY eff_gid
        ORDER BY {sort_col} {order}
        LIMIT ? OFFSET ?
    """
    page_rows = conn.execute(page_sql, params + [page_size, offset]).fetchall()
    page_eids = [r[0] for r in page_rows]

    if not page_eids:
        return [], total_count, {"total_count": total_count, "total_dist_km": total_dist}

    # Step 3: 해당 페이지 그룹 rows 로드
    group_ids: list[str] = []
    solo_ids: list[int] = []
    for eid, is_group in page_rows:
        if is_group:
            group_ids.append(eid)
        else:
            solo_ids.append(int(eid))

    all_rows: list[dict] = []
    cols_str = ", ".join(_COLS)
    if group_ids:
        ph = ",".join("?" * len(group_ids))
        rows = conn.execute(
            f"SELECT {cols_str} FROM activity_summaries WHERE matched_group_id IN ({ph})",
            group_ids,
        ).fetchall()
        all_rows.extend(dict(zip(_COLS, r)) for r in rows)
    if solo_ids:
        ph = ",".join("?" * len(solo_ids))
        rows = conn.execute(
            f"SELECT {cols_str} FROM activity_summaries WHERE id IN ({ph})",
            solo_ids,
        ).fetchall()
        all_rows.extend(dict(zip(_COLS, r)) for r in rows)

    # Step 4: Python 그룹화 → UnifiedActivity
    groups: dict[str, list[dict]] = {}
    for rd in all_rows:
        gid = rd.get("matched_group_id")
        eid = gid if gid else str(rd["id"])
        groups.setdefault(eid, []).append(rd)

    # WorkoutType 배치 로드 (N+1 방지)
    import json as _json
    _wt_cache: dict[int, dict] = {}
    all_act_ids = [rd["id"] for rd in all_rows]
    if all_act_ids:
        try:
            _ph = ",".join("?" * len(all_act_ids))
            _wt_rows = conn.execute(
                f"SELECT CAST(scope_id AS INTEGER), json_value FROM metric_store"
                f" WHERE scope_type='activity' AND scope_id IN ({_ph})"
                f"   AND metric_name='workout_type_classified'",
                [str(i) for i in all_act_ids],
            ).fetchall()
            for _aid, _mj in _wt_rows:
                if _mj:
                    try:
                        _wt_cache[_aid] = _json.loads(_mj)
                    except Exception:
                        pass
        except Exception:
            pass

    paged: list[UnifiedActivity] = []
    for eid in page_eids:
        g_rows = groups.get(eid)
        if not g_rows:
            continue
        gid = g_rows[0].get("matched_group_id")
        paged.append(build_unified_activity(gid, g_rows, _wt_cache=_wt_cache))

    stats = {"total_count": total_count, "total_dist_km": total_dist}
    return paged, total_count, stats


def build_source_comparison(source_rows: dict[str, dict]) -> list[dict]:
    """소스별 필드 비교 테이블 데이터 생성."""
    fields = [
        ("거리(m)", "distance_m"),
        ("시간(sec)", "duration_sec"),
        ("페이스(sec/km)", "avg_pace_sec_km"),
        ("평균 심박(bpm)", "avg_hr"),
        ("최대 심박(bpm)", "max_hr"),
        ("케이던스(spm)", "avg_cadence"),
        ("고도 상승(m)", "elevation_gain"),
        ("파워(W)", "avg_power"),
    ]
    rows = []
    for label, col in fields:
        unified = _pick_value(source_rows, col)
        row: dict[str, Any] = {
            "field": label,
            "unified_value": unified.value,
            "unified_source": unified.source,
        }
        for src in SERVICE_PRIORITY:
            if src in source_rows:
                row[src] = source_rows[src].get(col)
        rows.append(row)
    return rows
