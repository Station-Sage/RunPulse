"""활동 상세 — 데이터 로딩 함수."""
from __future__ import annotations

import json
import sqlite3

from src.services.unified_view import _COLS as _SUMMARY_COLS


def _fetch_source_rows(conn: sqlite3.Connection, activity_id: int) -> dict[str, dict]:
    """activity_id와 같은 그룹에 속한 모든 소스의 row 반환."""
    row = conn.execute(
        f"SELECT {', '.join(_SUMMARY_COLS)} FROM activity_summaries WHERE id = ?",
        (activity_id,),
    ).fetchone()
    if not row:
        return {}

    rd = dict(zip(_SUMMARY_COLS, row))
    group_id = rd.get("matched_group_id")

    if group_id:
        rows = conn.execute(
            f"SELECT {', '.join(_SUMMARY_COLS)} FROM activity_summaries "
            "WHERE matched_group_id = ?",
            (group_id,),
        ).fetchall()
    else:
        rows = [row]

    source_rows: dict[str, dict] = {}
    for r in rows:
        d = dict(zip(_SUMMARY_COLS, r))
        src = d["source"]
        if src not in source_rows:
            source_rows[src] = d

    # avg_power가 activity_summaries에 없으면 metric_store에서 보완
    for d in source_rows.values():
        if d.get("avg_power") is None:
            pw = conn.execute(
                "SELECT numeric_value FROM metric_store "
                "WHERE scope_type='activity' AND scope_id=CAST(? AS TEXT) AND metric_name = 'avg_power' AND is_primary=1 LIMIT 1",
                (str(d["id"]),),
            ).fetchone()
            if pw and pw[0] is not None:
                d["avg_power"] = pw[0]

    return source_rows


def _fetch_adjacent(conn, activity_id: int, start_time: str) -> tuple:
    """현재 활동 기준 이전/다음 활동 (id, date) 반환."""
    prev_row = conn.execute(
        """SELECT id, start_time FROM activity_summaries
           WHERE start_time < ? ORDER BY start_time DESC LIMIT 1""",
        (start_time,),
    ).fetchone()
    next_row = conn.execute(
        """SELECT id, start_time FROM activity_summaries
           WHERE start_time > ? ORDER BY start_time ASC LIMIT 1""",
        (start_time,),
    ).fetchone()
    return prev_row, next_row


def _load_activity_computed_metrics(conn: sqlite3.Connection, activity_id: int) -> dict:
    """활동별 metric_store 조회 → {metric_name: value} 딕셔너리."""
    rows = conn.execute(
        "SELECT metric_name, numeric_value FROM metric_store "
        "WHERE scope_type='activity' AND scope_id=CAST(? AS TEXT) AND is_primary=1",
        (str(activity_id),),
    ).fetchall()
    return {row[0]: row[1] for row in rows}


def _load_service_metrics(conn: sqlite3.Connection, activity_id: int) -> dict:
    """서비스 1차 메트릭 조회 (Garmin/Strava/Intervals 제공값).

    metric_store에서 provider별로 조회 후 소스별 섹션으로 구성.

    Returns:
        {service: {label: (value, unit)}} 딕셔너리.
    """
    anchor = conn.execute(
        "SELECT matched_group_id FROM activity_summaries WHERE id=?",
        (activity_id,),
    ).fetchone()
    if anchor is None:
        return {}

    group_id = anchor[0]
    if group_id:
        all_ids = [r[0] for r in conn.execute(
            "SELECT id FROM activity_summaries WHERE matched_group_id=?", (group_id,)
        ).fetchall()]
    else:
        all_ids = [activity_id]

    # metric_store에서 활동 메트릭 조회 (Phase 5-G: 6컬럼 포함)
    scope_ids = [str(aid) for aid in all_ids]
    ph = ",".join("?" * len(scope_ids))
    target_metrics = (
        "training_load", "training_effect_aerobic", "training_effect_anaerobic",
        "normalized_power", "suffer_score", "calories",
        "trimp", "hrss", "efficiency_factor", "intensity_factor",
        "aerobic_decoupling",
    )
    mph = ",".join("?" * len(target_metrics))

    ms_rows = conn.execute(
        f"SELECT provider, metric_name, numeric_value FROM metric_store"
        f" WHERE scope_type='activity' AND scope_id IN ({ph})"
        f" AND metric_name IN ({mph}) AND is_primary=1",
        scope_ids + list(target_metrics),
    ).fetchall()

    # provider → {metric_name: value}
    by_provider: dict[str, dict] = {}
    for provider, mname, val in ms_rows:
        if val is not None:
            by_provider.setdefault(provider, {})[mname] = val

    result: dict = {}

    g = by_provider.get("garmin", {})
    garmin: dict = {}
    if g.get("training_effect_aerobic") is not None:
        garmin["에어로빅 훈련 효과 (ATE)"] = (float(g["training_effect_aerobic"]), "/ 5.0")
    if g.get("training_effect_anaerobic") is not None:
        garmin["무산소 훈련 효과 (AnTE)"] = (float(g["training_effect_anaerobic"]), "/ 5.0")
    if g.get("training_load") is not None:
        garmin["훈련 부하"] = (float(g["training_load"]), "")
    if garmin:
        result["Garmin"] = garmin

    s = by_provider.get("strava", {})
    strava: dict = {}
    if s.get("suffer_score") is not None:
        strava["Suffer Score"] = (float(s["suffer_score"]), "")
    if s.get("normalized_power") is not None:
        strava["정규화 파워 (NP)"] = (float(s["normalized_power"]), " W")
    if strava:
        result["Strava"] = strava

    iv = by_provider.get("intervals", {})
    icu: dict = {}
    if iv.get("training_load") is not None:
        icu["훈련 부하 (Training Load)"] = (float(iv["training_load"]), "")
    if iv.get("trimp") is not None:
        icu["TRIMP"] = (float(iv["trimp"]), "")
    if iv.get("hrss") is not None:
        icu["HRSS"] = (float(iv["hrss"]), "")
    if iv.get("intensity_factor") is not None:
        icu["강도 (Intensity)"] = (float(iv["intensity_factor"]), "")
    if iv.get("efficiency_factor") is not None:
        icu["효율 계수 (EF)"] = (float(iv["efficiency_factor"]), "")
    if icu:
        result["Intervals.icu"] = icu

    return result


def _load_day_computed_metrics(conn: sqlite3.Connection, act_date: str) -> dict:
    """날짜별 metric_store 조회 (scope_type='daily') → {metric_name: value}."""
    rows = conn.execute(
        """SELECT metric_name, numeric_value FROM metric_store
           WHERE scope_id = ? AND scope_type='daily' AND is_primary=1""",
        (act_date,),
    ).fetchall()
    return {row[0]: row[1] for row in rows}


def _load_activity_metric_jsons(conn: sqlite3.Connection, activity_id: int) -> dict:
    """활동별 metric_store json_value 조회 → {metric_name: dict}."""
    rows = conn.execute(
        "SELECT metric_name, json_value FROM metric_store "
        "WHERE scope_type='activity' AND scope_id=CAST(? AS TEXT) AND is_primary=1 AND json_value IS NOT NULL",
        (str(activity_id),),
    ).fetchall()
    result = {}
    for name, mj in rows:
        try:
            result[name] = json.loads(mj)
        except Exception:
            pass
    return result


def _load_day_metric_jsons(conn: sqlite3.Connection, act_date: str) -> dict:
    """날짜별 metric_store json_value 조회 (scope_type='daily') → {metric_name: dict}."""
    rows = conn.execute(
        """SELECT metric_name, json_value FROM metric_store
           WHERE scope_id = ? AND scope_type='daily' AND is_primary=1 AND json_value IS NOT NULL""",
        (act_date,),
    ).fetchall()
    result = {}
    for name, mj in rows:
        try:
            result[name] = json.loads(mj)
        except Exception:
            pass
    return result


def _load_pmc_series(conn: sqlite3.Connection, target_date: str, days: int = 60) -> dict:
    """최근 N일 TRIMP_daily + ACWR 시계열 조회."""
    from datetime import date, timedelta
    end = date.fromisoformat(target_date)
    start = end - timedelta(days=days - 1)
    rows = conn.execute(
        """SELECT scope_id AS date, metric_name, numeric_value FROM metric_store
           WHERE scope_id BETWEEN ? AND ? AND scope_type='daily' AND is_primary=1
             AND metric_name IN ('trimp','acwr')
           ORDER BY scope_id""",
        (start.isoformat(), end.isoformat()),
    ).fetchall()
    dates_set: set[str] = set()
    trimp_map: dict[str, float] = {}
    acwr_map: dict[str, float] = {}
    for dt, mname, mval in rows:
        if mval is None:
            continue
        dates_set.add(dt)
        if mname == "trimp":
            trimp_map[dt] = round(float(mval), 1)
        elif mname == "acwr":
            acwr_map[dt] = round(float(mval), 3)
    dates = sorted(dates_set)
    return {
        "dates": dates,
        "trimp": [trimp_map.get(d) for d in dates],
        "acwr": [acwr_map.get(d) for d in dates],
        "target_date": target_date,
    }


def _extract_gap(source_rows: dict) -> float | None:
    """source_rows에서 GAP(sec/km)을 추출.

    우선순위: Intervals icu_gap(sec/km) → Garmin avg_grade_adjusted_speed(m/s 변환).
    """
    iv = source_rows.get("intervals") or {}
    if iv.get("icu_gap") is not None:
        return float(iv["icu_gap"])
    g = source_rows.get("garmin") or {}
    speed = g.get("avg_grade_adjusted_speed")
    if speed and float(speed) > 0:
        return round(1000.0 / float(speed), 1)
    return None


def _load_running_tolerance(conn: sqlite3.Connection, act_date: str) -> dict:
    """Running Tolerance 일별 데이터 조회."""
    rows = conn.execute(
        """SELECT metric_name, numeric_value FROM metric_store
           WHERE scope_id=? AND scope_type='daily' AND is_primary=1
             AND metric_name IN (
               'running_tolerance_load',
               'running_tolerance_optimal_max',
               'running_tolerance_score'
             )""",
        (act_date,),
    ).fetchall()
    return {r[0]: r[1] for r in rows if r[1] is not None}


def _load_hr_zone_times(source_rows: dict) -> list[float | None]:
    """HR 존 1~5 시간(초) 리스트 반환 (Garmin 소스 우선)."""
    garmin = source_rows.get("garmin") or {}
    zones = []
    for i in range(1, 6):
        v = garmin.get(f"hr_zone_time_{i}")
        zones.append(float(v) if v is not None else None)
    return zones


# 신규 loaders → views_activity_loaders_v2.py 로 분리
