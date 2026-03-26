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
    "id", "source", "source_id", "name", "activity_type", "start_time",
    "distance_km", "duration_sec", "avg_pace_sec_km", "avg_hr",
    "max_hr", "avg_cadence", "elevation_gain", "calories",
    "description", "matched_group_id", "workout_label", "avg_power",
    "event_type", "workout_type",
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
    event_type: UnifiedField = field(default_factory=UnifiedField)

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
        "event_type",
    ]:
        setattr(ua, fname, _pick_value(source_rows, fname))

    # RP 자동 분류 태그 주입
    try:
        import json as _json
        wt_row = conn.execute(
            "SELECT metric_json FROM computed_metrics WHERE activity_id=? AND metric_name='WorkoutType'",
            (rep_id,),
        ).fetchone()
        if wt_row and wt_row[0]:
            source_rows["_rp_workout_type"] = _json.loads(wt_row[0])
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

    # 정렬 컬럼 매핑: 그룹별 집계값으로 DB 정렬
    _DB_SORT_COL: dict[str, str] = {
        "date":     "MAX(start_time)",
        "distance": "MAX(distance_km)",
        "duration": "MAX(duration_sec)",
        "pace":     "MIN(CASE WHEN avg_pace_sec_km > 0 THEN avg_pace_sec_km END)",
        "hr":       "MAX(avg_hr)",
    }
    sort_col = _DB_SORT_COL.get(sort_by, "MAX(start_time)")
    order = "ASC" if sort_dir == "asc" else "DESC"

    # ── Step 1: 전체 그룹 수 + 통계 (DB 레벨) ───────────────────────────
    # 그룹별 1행으로 집계하여 total_count와 total_dist 계산
    stats_sql = f"""
        SELECT
            COUNT(*),
            COALESCE(SUM(rep_dist), 0)
        FROM (
            SELECT MAX(distance_km) AS rep_dist
            FROM activity_summaries
            {where}
            GROUP BY COALESCE(matched_group_id, CAST(id AS TEXT))
        )
    """
    stats_row = conn.execute(stats_sql, params).fetchone()
    total_count = stats_row[0] if stats_row else 0
    total_dist = float(stats_row[1]) if stats_row else 0.0

    # ── Step 2: 현재 페이지의 eff_gid 목록만 LIMIT/OFFSET으로 가져옴 ───
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

    # ── Step 3: 해당 페이지 그룹의 rows만 로드 ──────────────────────────
    # is_group 플래그로 구분 (matched_group_id는 숫자처럼 보이는 hex도 있음)
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

    # ── Step 4: Python에서 그룹화 → UnifiedActivity (현재 페이지 분만) ──
    groups: dict[str, list[dict]] = {}
    for rd in all_rows:
        gid = rd.get("matched_group_id")
        eid = gid if gid else str(rd["id"])
        groups.setdefault(eid, []).append(rd)

    # page_eids 순서(DB 정렬 순) 유지
    paged: list[UnifiedActivity] = []
    for eid in page_eids:
        g_rows = groups.get(eid)
        if not g_rows:
            continue
        gid = g_rows[0].get("matched_group_id")
        paged.append(build_unified_activity(gid, g_rows))

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
