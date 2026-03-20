"""단일 활동 심층 분석 — 4소스 통합 데이터 및 페이스 스플릿."""

import json
import sqlite3
from datetime import date

from src.utils.pace import seconds_to_pace


def _find_activity(
    conn: sqlite3.Connection,
    activity_id: int | None,
    date_str: str | None,
) -> tuple | None:
    """조건에 맞는 활동 행 반환.

    우선순위: activity_id > date_str > 오늘 날짜.

    Returns:
        (id, source, start_time, distance_km, duration_sec, avg_pace_sec_km,
         avg_hr, max_hr, avg_cadence, elevation_gain, calories, activity_type)
        또는 None.
    """
    cols = ("id, source, start_time, distance_km, duration_sec, avg_pace_sec_km, "
            "avg_hr, max_hr, avg_cadence, elevation_gain, calories, activity_type")

    if activity_id is not None:
        return conn.execute(
            f"SELECT {cols} FROM activity_summaries WHERE id = ?", (activity_id,)
        ).fetchone()

    target_date = date_str or date.today().isoformat()
    return conn.execute(
        f"SELECT {cols} FROM activity_summaries "
        "WHERE start_time >= ? AND start_time < ? AND activity_type IN ('running', 'run', 'virtualrun', 'treadmill', 'highintensityintervaltraining') "
        "ORDER BY start_time DESC LIMIT 1",
        (target_date, target_date + "T99"),
    ).fetchone()


def _get_group_activities(conn: sqlite3.Connection, activity_id: int) -> list[tuple]:
    """같은 그룹의 (id, source) 목록 반환.

    Args:
        activity_id: 기준 활동 id.

    Returns:
        [(id, source), ...] 리스트. 최소 기준 활동 자체가 포함된다.
    """
    row = conn.execute(
        "SELECT matched_group_id FROM activity_summaries WHERE id = ?", (activity_id,)
    ).fetchone()
    if not row:
        return [(activity_id, None)]

    group_id = row[0]
    if group_id:
        return conn.execute(
            "SELECT id, source FROM activity_summaries WHERE matched_group_id = ?",
            (group_id,),
        ).fetchall()
    return conn.execute(
        "SELECT id, source FROM activity_summaries WHERE id = ?", (activity_id,)
    ).fetchall()


def _get_metrics(conn: sqlite3.Connection, activity_id: int) -> dict:
    """activity_id의 source_metrics를 {metric_name: value_or_json} dict로 반환."""
    rows = conn.execute(
        "SELECT metric_name, metric_value, metric_json FROM activity_detail_metrics WHERE activity_id = ?",
        (activity_id,),
    ).fetchall()
    result = {}
    for name, val, js in rows:
        result[name] = js if val is None else val
    return result



def _get_daily_detail_metrics(
    conn: sqlite3.Connection,
    date: str,
    source: str = "garmin",
) -> dict:
    """일자별 daily_detail_metrics를 {metric_name: value_or_json} dict로 반환."""
    rows = conn.execute(
        "SELECT metric_name, metric_value, metric_json "
        "FROM daily_detail_metrics WHERE date = ? AND source = ?",
        (date, source),
    ).fetchall()
    result = {}
    for name, val, js in rows:
        result[name] = js if val is None else val
    return result

def _get_stream(conn: sqlite3.Connection, activity_id: int) -> dict | None:
    """같은 그룹 Strava 활동의 stream dict 반환."""
    row = conn.execute(
        "SELECT matched_group_id, source FROM activity_summaries WHERE id = ?", (activity_id,)
    ).fetchone()
    if not row:
        return None

    group_id, source = row[0], row[1]

    if group_id:
        strava_ids = conn.execute(
            "SELECT id FROM activity_summaries WHERE matched_group_id = ? AND source = 'strava'",
            (group_id,),
        ).fetchall()
    elif source == "strava":
        strava_ids = [(activity_id,)]
    else:
        strava_ids = []

    for (sid,) in strava_ids:
        r = conn.execute(
            "SELECT metric_json FROM activity_detail_metrics "
            "WHERE activity_id = ? AND metric_name = 'stream_file'",
            (sid,),
        ).fetchone()
        if r and r[0]:
            try:
                with open(r[0], "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    return {s["type"]: s["data"] for s in data
                            if "type" in s and "data" in s}
                return data
            except Exception:
                pass
    return None


def _calc_pace_splits(stream: dict) -> list[dict] | None:
    """Strava stream에서 1km 단위 페이스 스플릿 계산.

    Args:
        stream: {"time": [...], "distance": [...], "heartrate": [...], ...}

    Returns:
        [{"km": 1, "pace_sec": 325, "pace": "5:25", "avg_hr": 148}, ...] 또는 None.
    """
    times = stream.get("time", [])
    distances = stream.get("distance", [])
    heartrates = stream.get("heartrate")

    if not times or not distances or len(times) < 2:
        return None

    n = min(len(times), len(distances))
    splits = []
    km = 1
    target_m = 1000.0
    km_start_idx = 0

    for i in range(1, n):
        if distances[i] >= target_m:
            # 선형 보간으로 정확한 km 경계 시각 계산
            d_prev = distances[i - 1]
            d_curr = distances[i]
            if d_curr > d_prev:
                ratio = (target_m - d_prev) / (d_curr - d_prev)
                t_cross = times[i - 1] + ratio * (times[i] - times[i - 1])
            else:
                t_cross = float(times[i])

            t_start = float(times[km_start_idx])
            elapsed = t_cross - t_start
            pace_sec = max(1, round(elapsed))

            # 이 km 구간의 평균 심박
            avg_hr = None
            if heartrates and len(heartrates) >= n:
                hr_slice = heartrates[km_start_idx: i + 1]
                avg_hr = round(sum(hr_slice) / len(hr_slice)) if hr_slice else None

            splits.append({
                "km": km,
                "pace_sec": pace_sec,
                "pace": seconds_to_pace(pace_sec),
                "avg_hr": avg_hr,
            })

            km += 1
            target_m = km * 1000.0
            km_start_idx = i

    return splits if splits else None


def deep_analyze(
    conn: sqlite3.Connection,
    activity_id: int | None = None,
    date: str | None = None,
    config: dict | None = None,
) -> dict | None:
    """단일 활동 심층 분석 — 4소스 통합.

    Args:
        conn: SQLite 연결.
        activity_id: 직접 지정. None이면 date 사용.
        date: "YYYY-MM-DD" 형식. None이면 오늘.
        config: 설정 딕셔너리 (HR zone 등).

    Returns:
        4소스 통합 심층 분석 결과 dict, 활동 없으면 None.
    """
    # 지연 임포트 (순환 참조 방지)
    from src.analysis.efficiency import calculate_efficiency
    from src.analysis.zones_analysis import analyze_zones

    act_row = _find_activity(conn, activity_id, date)
    if not act_row:
        return None

    (act_id, act_source, start_time, dist_km, dur_sec,
     avg_pace, avg_hr, max_hr, avg_cadence, elev_gain, calories, act_type) = act_row

    act_date = start_time[:10]

    # 4소스 활동 및 metrics 수집
    group_acts = _get_group_activities(conn, act_id)
    source_metrics: dict[str, dict] = {}
    for (gid, gsrc) in group_acts:
        if gsrc:
            source_metrics[gsrc] = _get_metrics(conn, gid)

    # Garmin 지표
    g = source_metrics.get("garmin", {})
    garmin_data = {
        "training_effect_aerobic": g.get("training_effect_aerobic"),
        "training_effect_anaerobic": g.get("training_effect_anaerobic"),
        "training_load": g.get("training_load"),
        "vo2max": g.get("vo2max"),
    }

    # Strava 지표
    s = source_metrics.get("strava", {})
    best_efforts_raw = s.get("best_efforts")
    if isinstance(best_efforts_raw, str):
        try:
            best_efforts_raw = json.loads(best_efforts_raw)
        except Exception:
            best_efforts_raw = None

    # stream 및 pace splits
    stream = _get_stream(conn, act_id)
    pace_splits = _calc_pace_splits(stream) if stream else None

    strava_data = {
        "suffer_score": s.get("relative_effort"),
        "best_efforts": best_efforts_raw,
        "pace_splits": pace_splits,
    }

    # Intervals 지표
    iv = source_metrics.get("intervals", {})
    hr_zones_raw = iv.get("hr_zone_distribution")
    if isinstance(hr_zones_raw, str):
        try:
            hr_zones_raw = json.loads(hr_zones_raw)
        except Exception:
            hr_zones_raw = None

    intervals_data = {
        "icu_training_load": iv.get("icu_training_load"),
        "icu_hrss": iv.get("icu_hrss"),
        "icu_intensity": iv.get("icu_intensity"),
        "icu_efficiency_factor": iv.get("icu_efficiency_factor"),
        "decoupling": iv.get("decoupling"),
        "trimp": iv.get("trimp"),
        "average_stride": iv.get("average_stride"),
        "pace_zone_times": iv.get("pace_zone_times"),
        "icu_hr_zone_times": iv.get("icu_hr_zone_times"),
        "interval_summary": iv.get("interval_summary"),
        "hr_zones": hr_zones_raw,
    }

    # Runalyze 지표
    r = source_metrics.get("runalyze", {})
    race_pred_raw = r.get("race_prediction")
    if isinstance(race_pred_raw, str):
        try:
            race_pred_raw = json.loads(race_pred_raw)
        except Exception:
            race_pred_raw = None

    runalyze_data = {
        "effective_vo2max": r.get("effective_vo2max"),
        "vdot": r.get("vdot"),
        "trimp": r.get("trimp"),
        "marathon_shape": r.get("marathon_shape"),
        "race_predictions": race_pred_raw,
    }

    # 계산 모듈
    efficiency = calculate_efficiency(conn, act_id)
    zones = analyze_zones(conn, act_date, act_date + "T99", config)
    if zones.get("activity_count", 0) == 0:
        zones = None

    # daily_fitness 컨텍스트
    fitness_row = conn.execute(
        "SELECT ctl, atl, tsb, garmin_vo2max, runalyze_evo2max, runalyze_vdot "
        "FROM daily_fitness WHERE date = ? ORDER BY date DESC LIMIT 1",
        (act_date,),
    ).fetchone()
    fitness_ctx: dict = {
        "ctl": None, "atl": None, "tsb": None,
        "garmin_vo2max": None, "runalyze_evo2max": None, "runalyze_vdot": None,
    }
    if fitness_row:
        keys = list(fitness_ctx.keys())
        for i, k in enumerate(keys):
            fitness_ctx[k] = fitness_row[i]

    # daily_wellness 컨텍스트
    wellness_row = conn.execute(
        "SELECT body_battery, sleep_score, sleep_hours, hrv_value, stress_avg, resting_hr "
        "FROM daily_wellness WHERE date = ? AND source = 'garmin'",
        (act_date,),
    ).fetchone()
    recovery_ctx: dict = {
        "body_battery": None, "sleep_score": None, "sleep_hours": None,
        "hrv_value": None, "stress_level": None, "resting_hr": None,
    }
    if wellness_row:
        (recovery_ctx["body_battery"], recovery_ctx["sleep_score"],
         recovery_ctx["sleep_hours"], recovery_ctx["hrv_value"],
         recovery_ctx["stress_level"], recovery_ctx["resting_hr"]) = wellness_row

    daily_detail = _get_daily_detail_metrics(conn, act_date, source="garmin")
    garmin_daily_detail = {
        "sleep_stage_deep_sec": daily_detail.get("sleep_stage_deep_sec"),
        "sleep_stage_rem_sec": daily_detail.get("sleep_stage_rem_sec"),
        "sleep_restless_moments": daily_detail.get("sleep_restless_moments"),
        "overnight_hrv_avg": daily_detail.get("overnight_hrv_avg"),
        "overnight_hrv_sdnn": daily_detail.get("overnight_hrv_sdnn"),
        "hrv_baseline_low": daily_detail.get("hrv_baseline_low"),
        "hrv_baseline_high": daily_detail.get("hrv_baseline_high"),
        "body_battery_delta": daily_detail.get("body_battery_delta"),
        "stress_high_duration": daily_detail.get("stress_high_duration"),
        "respiration_avg": daily_detail.get("respiration_avg"),
        "spo2_avg": daily_detail.get("spo2_avg"),
        "training_readiness_score": daily_detail.get("training_readiness_score"),
    }

    # 평균 페이스 포맷
    avg_pace_str = seconds_to_pace(avg_pace) if avg_pace else None

    return {
        "activity": {
            "date": act_date,
            "type": act_type,
            "distance_km": dist_km,
            "duration_sec": dur_sec,
            "avg_pace": avg_pace_str,
            "avg_hr": avg_hr,
            "max_hr": max_hr,
            "avg_cadence": avg_cadence,
            "elevation_gain": elev_gain,
            "calories": calories,
        },
        "garmin": garmin_data,
        "garmin_daily_detail": garmin_daily_detail,
        "strava": strava_data,
        "intervals": intervals_data,
        "runalyze": runalyze_data,
        "calculated": {
            "efficiency": efficiency,
            "zones": zones,
        },
        "fitness_context": fitness_ctx,
        "recovery_context": recovery_ctx,
    }
