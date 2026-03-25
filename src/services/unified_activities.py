"""통합 활동 서비스 — 멀티 소스 활동을 Garmin 우선으로 병합."""
from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass, field
from typing import Any

SERVICE_PRIORITY = ["garmin", "strava", "intervals", "runalyze"]

# 소스 배지 색상
SOURCE_COLORS: dict[str, str] = {
    "garmin": "#0055b3",
    "strava": "#FC4C02",
    "intervals": "#00884e",
    "runalyze": "#7b2d8b",
}

_COLS = [
    "id", "source", "source_id", "activity_type", "start_time",
    "distance_km", "duration_sec", "avg_pace_sec_km", "avg_hr",
    "max_hr", "avg_cadence", "elevation_gain", "calories",
    "description", "matched_group_id", "workout_label", "avg_power",
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
    distance_km: UnifiedField = field(default_factory=UnifiedField)
    duration_sec: UnifiedField = field(default_factory=UnifiedField)
    avg_pace_sec_km: UnifiedField = field(default_factory=UnifiedField)
    avg_hr: UnifiedField = field(default_factory=UnifiedField)
    max_hr: UnifiedField = field(default_factory=UnifiedField)
    avg_cadence: UnifiedField = field(default_factory=UnifiedField)
    elevation_gain: UnifiedField = field(default_factory=UnifiedField)
    calories: UnifiedField = field(default_factory=UnifiedField)
    description: UnifiedField = field(default_factory=UnifiedField)
    workout_label: UnifiedField = field(default_factory=UnifiedField)

    @property
    def date(self) -> str:
        st = self.start_time.value
        s = str(st)
        # "YYYY-MM-DDTHH:MM:SS" or "YYYY-MM-DD HH:MM:SS" → "YYYY-MM-DD HH:MM"
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

    # 우선순위에 없는 소스라도 첫 번째 사용
    for src, v in all_values.items():
        return UnifiedField(value=v, source=src, all_values=all_values)

    return UnifiedField(value=None, source=None, all_values={})


def build_unified_activity(group_id: str | None, rows: list[dict]) -> UnifiedActivity:
    """row 목록(같은 그룹)으로 UnifiedActivity 생성.

    Args:
        group_id: matched_group_id. None이면 단일 소스 활동.
        rows: activity_summaries 행 dict 리스트.
    """
    is_real_group = group_id is not None
    source_rows: dict[str, dict] = {}
    for row in rows:
        src = row["source"]
        # 같은 소스가 여럿이면 첫 번째만 유지
        if src not in source_rows:
            source_rows[src] = row

    # representative_id: SERVICE_PRIORITY 기준 첫 소스의 id
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
        "activity_type", "start_time", "distance_km", "duration_sec",
        "avg_pace_sec_km", "avg_hr", "max_hr", "avg_cadence",
        "elevation_gain", "calories", "description", "workout_label",
    ]:
        setattr(ua, fname, _pick_value(source_rows, fname))

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
        conditions.append("distance_km >= ?")
        params.append(min_dist)

    if max_dist is not None:
        conditions.append("distance_km <= ?")
        params.append(max_dist)

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

    # 통합 그룹을 고려한 쿼리: 그룹에 속한 활동은 한 번만 집계
    # effective_group_id = COALESCE(matched_group_id, CAST(id AS TEXT))
    # 그룹별 대표 행(MIN(id)) + 소스 필터 시 그룹 전체를 가져와야 하므로
    # 전략: WHERE 절 적용 → 대상 effective_group_id 집합 → 해당 그룹의 모든 행 로드
    rows_sql = f"""
        SELECT {', '.join(_COLS)}
        FROM activity_summaries
        {where}
        ORDER BY start_time DESC
    """
    all_rows = conn.execute(rows_sql, params).fetchall()
    row_dicts = [dict(zip(_COLS, r)) for r in all_rows]

    # 그룹화: effective_group_id 기준으로 묶기
    # source_filter가 있어도 같은 그룹의 다른 소스 행도 포함해야 함
    group_ids_in_filter: set[str] = set()
    solo_ids_in_filter: set[int] = set()
    for rd in row_dicts:
        gid = rd.get("matched_group_id")
        if gid:
            group_ids_in_filter.add(gid)
        else:
            solo_ids_in_filter.add(rd["id"])

    # 그룹에 속한 행은 전체 소스 포함하여 다시 로드
    all_group_rows: list[dict] = []
    if group_ids_in_filter:
        gid_placeholders = ",".join("?" * len(group_ids_in_filter))
        g_rows = conn.execute(
            f"SELECT {', '.join(_COLS)} FROM activity_summaries "
            f"WHERE matched_group_id IN ({gid_placeholders})",
            list(group_ids_in_filter),
        ).fetchall()
        all_group_rows = [dict(zip(_COLS, r)) for r in g_rows]

    # 단일 소스 행 (solo)
    solo_rows = [rd for rd in row_dicts if rd["id"] in solo_ids_in_filter]

    # groups dict 구성
    groups: dict[str, list[dict]] = {}
    for rd in all_group_rows:
        gid = rd["matched_group_id"]
        groups.setdefault(gid, []).append(rd)
    for rd in solo_rows:
        eid = str(rd["id"])
        groups.setdefault(eid, []).append(rd)

    # UnifiedActivity 리스트 (시간 역순)
    unified_list: list[UnifiedActivity] = []
    seen: set[str] = set()
    # row_dicts 순서(start_time DESC)를 따름
    for rd in row_dicts:
        gid = rd.get("matched_group_id")
        eid = gid if gid else str(rd["id"])
        if eid in seen:
            continue
        seen.add(eid)
        g_rows = groups.get(eid, [rd])
        ua = build_unified_activity(gid, g_rows)
        unified_list.append(ua)

    # 정렬
    _SORT_KEY: dict[str, Any] = {
        "date":     lambda ua: ua.start_time.value or "",
        "distance": lambda ua: ua.distance_km.value or 0,
        "duration": lambda ua: ua.duration_sec.value or 0,
        "pace":     lambda ua: ua.avg_pace_sec_km.value or 0,
        "hr":       lambda ua: ua.avg_hr.value or 0,
    }
    key_fn = _SORT_KEY.get(sort_by, _SORT_KEY["date"])
    reverse = (sort_dir != "asc")
    unified_list.sort(key=key_fn, reverse=reverse)

    # 통계 (필터 기준)
    total_count = len(unified_list)
    total_dist = sum(
        (ua.distance_km.value or 0) for ua in unified_list
    )

    # 페이지네이션
    offset = (page - 1) * page_size
    paged = unified_list[offset: offset + page_size]

    stats = {"total_count": total_count, "total_dist_km": total_dist}
    return paged, total_count, stats


def build_source_comparison(source_rows: dict[str, dict]) -> list[dict]:
    """소스별 필드 비교 테이블 데이터 생성.

    각 row에 통합값(unified_value)과 출처(unified_source)를 포함한다.

    Returns:
        [{"field": "거리(km)", "unified_value": 10.12, "unified_source": "garmin",
          "garmin": 10.12, "strava": 10.08, ...}, ...]
    """
    fields = [
        ("거리(km)", "distance_km"),
        ("시간(sec)", "duration_sec"),
        ("페이스(sec/km)", "avg_pace_sec_km"),
        ("평균 심박(bpm)", "avg_hr"),
        ("최대 심박(bpm)", "max_hr"),
        ("케이던스(spm)", "avg_cadence"),
        ("고도 상승(m)", "elevation_gain"),
        ("파워(W)", "avg_power"),
        ("칼로리(kcal)", "calories"),
    ]
    # avg_power가 activity_detail_metrics에만 있는 경우 source_rows에 보완
    for src, row in source_rows.items():
        if row.get("avg_power") is None:
            # avg_power는 DB에서 JOIN 없이는 안 오는 경우도 있으므로 graceful
            pass
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


def assign_group_to_activities(
    conn: sqlite3.Connection, activity_ids: list[int]
) -> str:
    """activity_ids를 하나의 그룹으로 묶기.

    선택된 활동 중 이미 그룹에 속한 것이 있으면 해당 그룹의 모든 멤버도
    함께 묶는다 (그룹 병합). 기존 group_id가 있으면 재사용한다.

    Returns:
        할당한 group_id (UUID 문자열).
    """
    if len(activity_ids) < 2:
        raise ValueError("2개 이상 활동이 필요합니다.")

    placeholders = ",".join("?" * len(activity_ids))

    # 선택된 활동 및 이들이 속한 기존 그룹의 모든 멤버 ID + 기존 group_id 수집
    rows = conn.execute(
        f"SELECT id, matched_group_id FROM activity_summaries WHERE id IN ({placeholders})",
        activity_ids,
    ).fetchall()

    existing_group_ids = {r[1] for r in rows if r[1] is not None}

    # 기존 group_id가 있으면 첫 번째 것을 재사용, 없으면 새로 생성
    group_id = next(iter(existing_group_ids), None) or str(uuid.uuid4())

    # 기존 그룹에 속한 모든 멤버도 포함
    all_ids = set(activity_ids)
    if existing_group_ids:
        gid_placeholders = ",".join("?" * len(existing_group_ids))
        member_rows = conn.execute(
            f"SELECT id FROM activity_summaries WHERE matched_group_id IN ({gid_placeholders})",
            list(existing_group_ids),
        ).fetchall()
        all_ids.update(r[0] for r in member_rows)

    all_placeholders = ",".join("?" * len(all_ids))
    conn.execute(
        f"UPDATE activity_summaries SET matched_group_id = ? WHERE id IN ({all_placeholders})",
        [group_id, *all_ids],
    )
    conn.commit()
    return group_id


def remove_from_group(conn: sqlite3.Connection, activity_id: int) -> None:
    """활동을 그룹에서 분리 (matched_group_id = NULL)."""
    conn.execute(
        "UPDATE activity_summaries SET matched_group_id = NULL WHERE id = ?",
        (activity_id,),
    )
    conn.commit()
