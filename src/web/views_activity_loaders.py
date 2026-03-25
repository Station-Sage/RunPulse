"""활동 상세 — 데이터 로딩 함수."""
from __future__ import annotations

import json
import sqlite3

from src.services.unified_activities import _COLS as _SUMMARY_COLS


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

    # avg_power가 activity_summaries에 없으면 activity_detail_metrics에서 보완
    for d in source_rows.values():
        if d.get("avg_power") is None:
            pw = conn.execute(
                "SELECT metric_value FROM activity_detail_metrics "
                "WHERE activity_id = ? AND metric_name = 'avg_power' LIMIT 1",
                (d["id"],),
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
    """활동별 computed_metrics 조회 → {metric_name: value} 딕셔너리."""
    rows = conn.execute(
        "SELECT metric_name, metric_value FROM computed_metrics WHERE activity_id = ?",
        (activity_id,),
    ).fetchall()
    return {row[0]: row[1] for row in rows}


def _load_service_metrics(conn: sqlite3.Connection, activity_id: int) -> dict:
    """서비스 1차 메트릭 조회 (Garmin/Strava/Intervals 제공값).

    그룹 내 모든 소스 row를 조회하여 각 소스별 데이터를 정확히 반환.

    Returns:
        {service: {label: (value, unit)}} 딕셔너리.
    """
    # 대표 활동의 matched_group_id 조회
    anchor = conn.execute(
        "SELECT matched_group_id FROM activity_summaries WHERE id=?",
        (activity_id,),
    ).fetchone()
    if anchor is None:
        return {}

    group_id = anchor[0]
    cols = ("source, aerobic_training_effect, anaerobic_training_effect, training_load,"
            " suffer_score, avg_power, normalized_power,"
            " icu_training_load, icu_trimp, icu_hrss,"
            " icu_intensity, icu_efficiency_factor, icu_atl, icu_ctl, icu_tsb")

    if group_id:
        raw_rows = conn.execute(
            f"SELECT {cols} FROM activity_summaries WHERE matched_group_id=?",
            (group_id,),
        ).fetchall()
    else:
        raw_rows = conn.execute(
            f"SELECT {cols} FROM activity_summaries WHERE id=?",
            (activity_id,),
        ).fetchall()

    # source → row dict
    src_map: dict[str, tuple] = {}
    for r in raw_rows:
        src = r[0] or ""
        if src not in src_map:
            src_map[src] = r

    result: dict = {}

    g = src_map.get("garmin") or src_map.get("", ())
    if g:
        garmin = {}
        if g[1] is not None:
            garmin["에어로빅 훈련 효과 (ATE)"] = (float(g[1]), "/ 5.0")
        if g[2] is not None:
            garmin["무산소 훈련 효과 (AnTE)"] = (float(g[2]), "/ 5.0")
        if g[3] is not None:
            garmin["훈련 부하"] = (float(g[3]), "")
        if garmin:
            result["Garmin"] = garmin

    s = src_map.get("strava", ())
    if s:
        strava = {}
        if s[4] is not None:
            strava["Suffer Score"] = (float(s[4]), "")
        if s[5] is not None:
            strava["평균 파워"] = (float(s[5]), " W")
        if s[6] is not None:
            strava["정규화 파워 (NP)"] = (float(s[6]), " W")
        if strava:
            result["Strava"] = strava

    iv = src_map.get("intervals", ())
    if iv:
        icu = {}
        if iv[7] is not None:
            icu["훈련 부하 (Training Load)"] = (float(iv[7]), "")
        if iv[8] is not None:
            icu["TRIMP"] = (float(iv[8]), "")
        if iv[9] is not None:
            icu["HRSS"] = (float(iv[9]), "")
        if iv[10] is not None:
            icu["강도 (Intensity)"] = (float(iv[10]), "")
        if iv[11] is not None:
            icu["효율 계수 (EF)"] = (float(iv[11]), "")
        if iv[12] is not None:
            icu["ATL"] = (float(iv[12]), "")
        if iv[13] is not None:
            icu["CTL"] = (float(iv[13]), "")
        if iv[14] is not None:
            icu["TSB"] = (float(iv[14]), "")
        if icu:
            result["Intervals.icu"] = icu

    # activity_detail_metrics에서 날씨 + zone 스코어 (그룹 내 모든 활동 포함)
    if group_id:
        all_ids = [r[0] for r in conn.execute(
            "SELECT id FROM activity_summaries WHERE matched_group_id=?", (group_id,)
        ).fetchall()]
    else:
        all_ids = [activity_id]
    ph = ",".join("?" * len(all_ids))
    detail_rows = conn.execute(
        f"""SELECT metric_name, metric_value FROM activity_detail_metrics
           WHERE activity_id IN ({ph}) AND metric_name IN (
             'weather_temp_c','weather_humidity_pct','weather_wind_speed_ms',
             'heartrate_zone_score','power_zone_score'
           )""",
        all_ids,
    ).fetchall()
    detail = {r[0]: r[1] for r in detail_rows if r[1] is not None}

    weather = {}
    if "weather_temp_c" in detail:
        weather["기온"] = (float(detail["weather_temp_c"]), " °C")
    if "weather_humidity_pct" in detail:
        weather["습도"] = (float(detail["weather_humidity_pct"]), " %")
    if "weather_wind_speed_ms" in detail:
        weather["풍속"] = (float(detail["weather_wind_speed_ms"]), " m/s")
    if weather:
        result["날씨 (서비스)"] = weather

    zones_svc = {}
    if "heartrate_zone_score" in detail:
        zones_svc["HR Zone Score (Strava)"] = (float(detail["heartrate_zone_score"]), "")
    if "power_zone_score" in detail:
        zones_svc["Power Zone Score (Strava)"] = (float(detail["power_zone_score"]), "")
    if zones_svc:
        result["존 점수 (서비스)"] = zones_svc

    return result


def _load_day_computed_metrics(conn: sqlite3.Connection, act_date: str) -> dict:
    """날짜별 computed_metrics 조회 (activity_id IS NULL) → {metric_name: value}."""
    rows = conn.execute(
        """SELECT metric_name, metric_value FROM computed_metrics
           WHERE date = ? AND activity_id IS NULL""",
        (act_date,),
    ).fetchall()
    return {row[0]: row[1] for row in rows}


def _load_activity_metric_jsons(conn: sqlite3.Connection, activity_id: int) -> dict:
    """활동별 computed_metrics metric_json 조회 → {metric_name: dict}."""
    rows = conn.execute(
        "SELECT metric_name, metric_json FROM computed_metrics WHERE activity_id = ? AND metric_json IS NOT NULL",
        (activity_id,),
    ).fetchall()
    result = {}
    for name, mj in rows:
        try:
            result[name] = json.loads(mj)
        except Exception:
            pass
    return result


def _load_day_metric_jsons(conn: sqlite3.Connection, act_date: str) -> dict:
    """날짜별 computed_metrics metric_json 조회 (activity_id IS NULL) → {metric_name: dict}."""
    rows = conn.execute(
        """SELECT metric_name, metric_json FROM computed_metrics
           WHERE date = ? AND activity_id IS NULL AND metric_json IS NOT NULL""",
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
        """SELECT date, metric_name, metric_value FROM computed_metrics
           WHERE date BETWEEN ? AND ? AND activity_id IS NULL
             AND metric_name IN ('TRIMP_daily','ACWR')
           ORDER BY date""",
        (start.isoformat(), end.isoformat()),
    ).fetchall()
    dates_set: set[str] = set()
    trimp_map: dict[str, float] = {}
    acwr_map: dict[str, float] = {}
    for dt, mname, mval in rows:
        if mval is None:
            continue
        dates_set.add(dt)
        if mname == "TRIMP_daily":
            trimp_map[dt] = round(float(mval), 1)
        elif mname == "ACWR":
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
