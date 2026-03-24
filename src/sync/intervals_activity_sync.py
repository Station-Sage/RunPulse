"""Intervals.icu 활동 동기화 (Activity List + Detail + Intervals + Streams)."""

import json
import sqlite3
from datetime import datetime, timedelta

from src.utils import api
from src.utils.api import ApiError
from src.utils.dedup import assign_group_id
from src.utils.raw_payload import update_changed_fields
from src.utils.raw_payload import store_raw_payload as _store_rp

from .intervals_auth import base_url, auth


def _store_raw(
    conn: sqlite3.Connection,
    entity_type: str,
    entity_id: str,
    payload: dict,
    activity_id: int | None = None,
) -> None:
    _store_rp(conn, "intervals", entity_type, entity_id, payload, activity_id=activity_id)


def _upsert_activity_metrics(
    conn: sqlite3.Connection,
    activity_id: int,
    act: dict,
) -> None:
    """Intervals activity metrics 저장 (activity_detail_metrics)."""
    try:
        conn.execute(
            "DELETE FROM activity_detail_metrics WHERE source = 'intervals' AND activity_id = ?",
            (activity_id,),
        )
    except sqlite3.Error:
        pass

    numeric_metrics = {
        "icu_training_load": act.get("icu_training_load"),
        "icu_intensity": act.get("icu_intensity"),
        "icu_hrss": act.get("icu_hrss"),
        "trimp": act.get("trimp"),
        "strain_score": act.get("strain_score"),
        "icu_efficiency_factor": act.get("icu_efficiency_factor"),
        "decoupling": act.get("decoupling"),
        "hr_load": act.get("hr_load"),
        "pace_load": act.get("pace_load"),
        "power_load": act.get("power_load"),
        "session_rpe": act.get("session_rpe"),
        "average_stride": act.get("average_stride"),
        "icu_lap_count": act.get("icu_lap_count"),
        "icu_ftp": act.get("icu_ftp"),
        "icu_rolling_ftp": act.get("icu_rolling_ftp"),
        "icu_pm_ftp": act.get("icu_pm_ftp"),
        "icu_pm_ftp_watts": act.get("icu_pm_ftp_watts"),
        "icu_pm_cp": act.get("icu_pm_cp"),
        "icu_variability_index": act.get("icu_variability_index"),
        "icu_weighted_avg_watts": act.get("icu_weighted_avg_watts"),
        "icu_average_watts": act.get("icu_average_watts"),
        "gap": act.get("gap"),
        "normalized_power": act.get("icu_weighted_avg_watts"),
        "max_speed": act.get("max_speed"),
        "max_power": act.get("p_max"),
        "elevation_loss": act.get("total_elevation_loss"),
        "avg_run_cadence": act.get("average_cadence"),
        "avg_temp_c": act.get("average_weather_temp"),
        "weather_wind_speed": act.get("average_wind_speed"),
        "weather_wind_gust": act.get("average_wind_gust"),
        "weather_feels_like": act.get("average_feels_like"),
        "weather_clouds": act.get("average_clouds"),
        "polarization_index": act.get("polarization_index"),
        "icu_power_hr": act.get("icu_power_hr"),
    }
    for name, value in numeric_metrics.items():
        if value is not None:
            try:
                conn.execute(
                    """INSERT INTO activity_detail_metrics
                       (activity_id, source, metric_name, metric_value)
                       VALUES (?, 'intervals', ?, ?)""",
                    (activity_id, name, float(value)),
                )
            except sqlite3.Error:
                pass

    json_metrics = [
        ("icu_zone_times", act.get("icu_zone_times")),
        ("icu_hr_zone_times", act.get("icu_hr_zone_times")),
        ("pace_zone_times", act.get("pace_zone_times")),
        ("gap_zone_times", act.get("gap_zone_times")),
        ("interval_summary", act.get("interval_summary")),
        ("stream_types", act.get("stream_types")),
    ]
    for metric_name, payload in json_metrics:
        if payload not in (None, [], {}):
            try:
                conn.execute(
                    """INSERT INTO activity_detail_metrics
                       (activity_id, source, metric_name, metric_json)
                       VALUES (?, 'intervals', ?, ?)""",
                    (activity_id, metric_name, json.dumps(payload, ensure_ascii=False)),
                )
            except sqlite3.Error:
                pass


def _sync_activity_intervals(
    conn: sqlite3.Connection,
    source_id: str,
    activity_id: int,
    auth_tuple: tuple,
    base: str,
) -> None:
    """Intervals.icu /activities/{id}/intervals → activity_laps 저장."""
    try:
        intervals = api.get(
            f"{base}/activities/{source_id}/intervals",
            auth=auth_tuple,
        )
    except ApiError as e:
        if e.status_code != 404:
            print(f"[intervals] 인터벌 조회 실패 {source_id}: {e}")
        return
    except Exception as e:
        print(f"[intervals] 인터벌 조회 실패 {source_id}: {e}")
        return

    for i, interval in enumerate(intervals or []):
        dist = (interval.get("distance") or 0) / 1000.0
        dur = interval.get("moving_time") or interval.get("elapsed_time")
        pace = round(dur / dist) if dist > 0 and dur else None
        cadence = interval.get("average_cadence")
        if cadence:
            cadence = int(cadence * 2)
        try:
            conn.execute(
                """INSERT OR IGNORE INTO activity_laps
                   (activity_id, source, lap_index, distance_km, duration_sec,
                    avg_pace_sec_km, avg_hr, max_hr, avg_cadence,
                    elevation_gain, avg_power, max_power, avg_speed_ms, max_speed_ms,
                    normalized_power)
                   VALUES (?, 'intervals', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    activity_id, i,
                    dist, dur, pace,
                    interval.get("average_heartrate"), interval.get("max_heartrate"),
                    cadence,
                    interval.get("total_elevation_gain"),
                    interval.get("average_watts"), interval.get("max_watts"),
                    interval.get("average_speed"), interval.get("max_speed"),
                    interval.get("normalized_power"),
                ),
            )
        except Exception:
            pass


def _sync_activity_streams(
    conn: sqlite3.Connection,
    source_id: str,
    activity_id: int,
    auth_tuple: tuple,
    base: str,
    force: bool = False,
) -> int:
    """Intervals.icu 활동 스트림 → activity_streams 저장."""
    if not force:
        existing = conn.execute(
            "SELECT COUNT(*) FROM activity_streams WHERE activity_id = ? AND source = 'intervals'",
            (activity_id,),
        ).fetchone()[0]
        if existing > 0:
            return 0

    if force:
        conn.execute(
            "DELETE FROM activity_streams WHERE activity_id = ? AND source = 'intervals'",
            (activity_id,),
        )

    try:
        streams = api.get(
            f"{base}/activities/{source_id}/streams",
            auth=auth_tuple,
        )
    except ApiError as e:
        if e.status_code != 404:
            print(f"[intervals] 스트림 조회 실패 {source_id}: {e}")
        return 0
    except Exception as e:
        print(f"[intervals] 스트림 조회 실패 {source_id}: {e}")
        return 0

    if not streams:
        return 0

    # Intervals.icu streams: {"watts": [...], "heartrate": [...], ...}
    rows = []
    if isinstance(streams, dict):
        for stream_type, data in streams.items():
            if isinstance(data, list) and data:
                rows.append((
                    activity_id, "intervals", stream_type,
                    json.dumps(data),
                    len(data),
                ))
    elif isinstance(streams, list):
        for s in streams:
            if isinstance(s, dict) and "type" in s and s.get("data"):
                rows.append((
                    activity_id, "intervals", s["type"],
                    json.dumps(s["data"]),
                    len(s["data"]),
                ))

    if rows:
        conn.executemany(
            """INSERT OR IGNORE INTO activity_streams
               (activity_id, source, stream_type, data_json, original_size)
               VALUES (?, ?, ?, ?, ?)""",
            rows,
        )

    return len(rows)


def _sync_power_curve(
    conn: sqlite3.Connection,
    source_id: str,
    activity_id: int,
    auth_tuple: tuple,
    base: str,
) -> None:
    """Intervals.icu /activities/{id}/power_curve → activity_detail_metrics 저장."""
    try:
        data = api.get(
            f"{base}/activities/{source_id}/power_curve",
            auth=auth_tuple,
        )
    except ApiError as e:
        if e.status_code != 404:
            print(f"[intervals] power_curve 조회 실패 {source_id}: {e}")
        return
    except Exception as e:
        print(f"[intervals] power_curve 조회 실패 {source_id}: {e}")
        return

    if not data:
        return

    try:
        conn.execute(
            """INSERT OR IGNORE INTO activity_detail_metrics
               (activity_id, source, metric_name, metric_json)
               VALUES (?, 'intervals', 'power_curve', ?)""",
            (activity_id, json.dumps(data, ensure_ascii=False)),
        )
    except sqlite3.Error:
        pass


def sync_activities(
    config: dict,
    conn: sqlite3.Connection,
    days: int,
    from_date: str | None = None,
    to_date: str | None = None,
) -> int:
    """Intervals.icu 활동 데이터를 가져와 DB에 저장.

    Args:
        config: 전체 설정 딕셔너리.
        conn: SQLite 연결.
        days: 가져올 일수 (from_date 미지정 시 사용).
        from_date: 기간 동기화 시작일 (YYYY-MM-DD). 지정 시 days 무시.
        to_date: 기간 동기화 종료일 (YYYY-MM-DD). None이면 오늘.

    Returns:
        새로 저장된 활동 수.
    """
    base = base_url(config)
    auth_tuple = auth(config)
    force_streams = bool(from_date)

    if from_date:
        oldest = from_date
        newest = to_date if to_date else datetime.now().strftime("%Y-%m-%d")
    else:
        oldest = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        newest = datetime.now().strftime("%Y-%m-%d")

    activity_list = api.get(
        f"{base}/activities",
        params={"oldest": oldest, "newest": newest},
        auth=auth_tuple,
    )
    count = 0

    for act in activity_list:
        source_id = str(act.get("id", ""))
        distance_km = (act.get("distance") or 0) / 1000
        duration_sec = int(act.get("moving_time") or 0)
        avg_pace = round(duration_sec / distance_km) if distance_km > 0 else None
        start_time = act.get("start_date_local", "").rstrip("Z")

        raw_cadence = act.get("average_cadence")
        avg_cadence = int(raw_cadence * 2) if raw_cadence is not None else None

        tags = act.get("tags")
        workout_label = ", ".join(tags) if tags else None

        # icu_* 필드 직접 activity_summaries에 저장
        icu_tsb = act.get("form")  # Intervals.icu는 form = CTL - ATL

        start_latlng = act.get("start_latlng") or [None, None]
        start_lat = start_latlng[0] if len(start_latlng) > 0 else None
        start_lon = start_latlng[1] if len(start_latlng) > 1 else None

        try:
            cursor = conn.execute(
                """INSERT OR IGNORE INTO activity_summaries
                   (source, source_id, name, activity_type, sport_type, start_time,
                    distance_km, duration_sec, moving_time_sec, elapsed_time_sec,
                    avg_pace_sec_km, avg_hr, max_hr, avg_cadence,
                    avg_speed_ms, max_speed_ms, elevation_gain, elevation_loss,
                    calories, workout_label, avg_power, normalized_power,
                    start_lat, start_lon,
                    icu_training_load, icu_trimp, icu_hrss,
                    icu_intensity, icu_atl, icu_ctl, icu_tsb,
                    icu_gap, icu_decoupling, icu_efficiency_factor)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    "intervals", source_id,
                    act.get("name"),
                    act.get("type", "Run").lower(),
                    act.get("sport_type"),
                    start_time,
                    distance_km, duration_sec,
                    act.get("moving_time"),
                    act.get("elapsed_time"),
                    avg_pace,
                    act.get("average_heartrate"), act.get("max_heartrate"),
                    avg_cadence,
                    act.get("average_speed"), act.get("max_speed"),
                    act.get("total_elevation_gain"),
                    act.get("total_elevation_loss"),
                    act.get("calories"),
                    workout_label,
                    act.get("icu_weighted_avg_watts"),
                    act.get("icu_weighted_avg_watts"),
                    start_lat, start_lon,
                    act.get("icu_training_load"),
                    act.get("trimp"),
                    act.get("icu_hrss"),
                    act.get("icu_intensity"),
                    act.get("atl"),
                    act.get("ctl"),
                    icu_tsb,
                    act.get("gap"),
                    act.get("decoupling"),
                    act.get("icu_efficiency_factor"),
                ),
            )
        except sqlite3.Error as e:
            print(f"[intervals] 활동 삽입 실패 {source_id}: {e}")
            continue

        if cursor.rowcount == 0:
            existing_id = update_changed_fields(conn, "intervals", source_id, {
                "avg_hr": act.get("average_heartrate"),
                "max_hr": act.get("max_heartrate"),
                "avg_cadence": avg_cadence,
                "elevation_gain": act.get("total_elevation_gain"),
                "elevation_loss": act.get("total_elevation_loss"),
                "calories": act.get("calories"),
                "name": act.get("name"),
                "workout_label": workout_label,
                "avg_power": act.get("icu_weighted_avg_watts"),
                "icu_training_load": act.get("icu_training_load"),
                "icu_trimp": act.get("trimp"),
                "icu_hrss": act.get("icu_hrss"),
                "icu_intensity": act.get("icu_intensity"),
                "icu_atl": act.get("atl"),
                "icu_ctl": act.get("ctl"),
                "icu_tsb": icu_tsb,
                "icu_gap": act.get("gap"),
                "icu_decoupling": act.get("decoupling"),
                "icu_efficiency_factor": act.get("icu_efficiency_factor"),
            })
            _store_raw(conn, "activity", source_id, act, activity_id=existing_id)
            if existing_id:
                _upsert_activity_metrics(conn, existing_id, act)
            continue

        activity_id = cursor.lastrowid
        count += 1
        _store_raw(conn, "activity", source_id, act, activity_id=activity_id)
        _upsert_activity_metrics(conn, activity_id, act)

        # 인터벌(랩) + 스트림 (신규 활동)
        try:
            _sync_activity_intervals(conn, source_id, activity_id, auth_tuple, base)
        except Exception as e:
            print(f"[intervals] 인터벌 저장 실패 {source_id}: {e}")

        try:
            _sync_activity_streams(conn, source_id, activity_id, auth_tuple, base, force=force_streams)
        except Exception as e:
            print(f"[intervals] 스트림 저장 실패 {source_id}: {e}")

        try:
            _sync_power_curve(conn, source_id, activity_id, auth_tuple, base)
        except Exception as e:
            print(f"[intervals] power_curve 저장 실패 {source_id}: {e}")

        assign_group_id(conn, activity_id)

    conn.commit()
    return count
