from __future__ import annotations

"""Garmin 활동 확장 API — streams, gear, exercise_sets, weather, hr/power zones."""

import json
import sqlite3
from typing import TYPE_CHECKING

from src.sync.garmin_helpers import _store_raw_payload

if TYPE_CHECKING:
    from garminconnect import Garmin


def sync_activity_streams(
    conn: sqlite3.Connection,
    client: "Garmin",
    activity_id: int,
    source_id: str,
    force: bool = False,
) -> int:
    """Garmin activity_details GPS/시계열 → activity_streams 저장.

    Args:
        force: True이면 기존 스트림 삭제 후 재저장 (기간 동기화용).

    Returns:
        저장된 스트림 타입 수.
    """
    if not force:
        existing = conn.execute(
            "SELECT COUNT(*) FROM activity_streams "
            "WHERE activity_id = ? AND source = 'garmin'",
            (activity_id,),
        ).fetchone()[0]
        if existing > 0:
            return 0

    try:
        data = client.get_activity_details(int(source_id), maxpoly=9999999)
    except Exception as e:
        print(f"[garmin] activity_details 조회 실패 {source_id}: {e}")
        return 0

    if not data:
        return 0

    _store_raw_payload(conn, "activity_details", source_id, data, activity_id=activity_id)

    streams = _parse_garmin_streams_by_type(data)
    if not streams:
        return 0

    if force:
        conn.execute(
            "DELETE FROM activity_streams WHERE activity_id = ? AND source = 'garmin'",
            (activity_id,),
        )

    rows = [
        (activity_id, "garmin", stype, json.dumps(arr), len(arr))
        for stype, arr in streams.items()
    ]
    conn.executemany(
        """INSERT OR IGNORE INTO activity_streams
           (activity_id, source, stream_type, data_json, original_size)
           VALUES (?, ?, ?, ?, ?)""",
        rows,
    )
    return len(rows)


def _parse_garmin_streams_by_type(data: dict) -> dict[str, list]:
    """Garmin metricDescriptors + activityDetailMetrics → {stream_type: [values...]}."""
    descriptors = data.get("metricDescriptors", [])
    if not descriptors:
        return {}

    # Garmin metric key → standard stream_type name
    key_map = {
        "directLatitude": "latlng_lat",
        "directLongitude": "latlng_lon",
        "directElevation": "altitude",
        "directDistance": "distance",
        "directSpeed": "velocity_smooth",
        "directHeartRate": "heartrate",
        "directDoubleCadence": "cadence",
        "directPower": "watts",
        "directAirTemperature": "temp",
        "directTemperature": "temp",
        "sumAccumulatedPower": "accumulated_power",
    }

    idx_map: dict[str, int] = {}
    for d in descriptors:
        k = d.get("key") or d.get("metricsKey")
        idx = d.get("metricsIndex")
        if k is not None and idx is not None:
            idx_map[k] = int(idx)

    # Initialize per-type arrays for found keys
    streams: dict[str, list] = {}
    for garmin_key, stream_name in key_map.items():
        if garmin_key in idx_map and stream_name not in streams:
            streams[stream_name] = []

    for row in data.get("activityDetailMetrics", []):
        metrics = row.get("metrics", [])
        for garmin_key, stream_name in key_map.items():
            if garmin_key not in idx_map:
                continue
            idx = idx_map[garmin_key]
            val = metrics[idx] if idx < len(metrics) else None
            if stream_name not in streams:
                streams[stream_name] = []
            # temp: don't overwrite if already set by directAirTemperature
            if garmin_key == "directTemperature" and streams.get(stream_name):
                continue
            streams[stream_name].append(val)

    return {k: v for k, v in streams.items() if v and any(x is not None for x in v)}


def sync_activity_gear(
    conn: sqlite3.Connection,
    client: "Garmin",
    activity_id: int,
    source_id: str,
) -> str | None:
    """Garmin 활동 장비 → gear 테이블 저장 및 activity_summaries 링크.

    Returns:
        저장된 gear_id (첫 번째), 없으면 None.
    """
    try:
        data = client.get_activity_gear(int(source_id))
    except Exception as e:
        print(f"[garmin] activity_gear 조회 실패 {source_id}: {e}")
        return None

    if not data:
        return None

    _store_raw_payload(conn, "activity_gear", source_id, {"gear": data}, activity_id=activity_id)

    gear_list = data if isinstance(data, list) else [data]
    first_gear_id = None

    for item in gear_list:
        g_id = str(item.get("gearPk") or item.get("uuid") or "")
        if not g_id:
            continue
        name = (
            item.get("customMakeModel") or item.get("displayName")
            or item.get("name") or ""
        )
        dist_km = item.get("totalDistanceInKilometers")
        dist_m = dist_km * 1000 if dist_km is not None else item.get("totalDistance")
        retired = 1 if (item.get("gearStatusName") or "").lower() == "inactive" else 0

        try:
            conn.execute(
                """INSERT INTO gear (source, source_gear_id, name, distance_m, retired)
                   VALUES ('garmin', ?, ?, ?, ?)
                   ON CONFLICT(source, source_gear_id) DO UPDATE SET
                       name = COALESCE(excluded.name, name),
                       distance_m = excluded.distance_m,
                       retired = excluded.retired,
                       updated_at = datetime('now')""",
                (g_id, name, dist_m, retired),
            )
        except sqlite3.Error as e:
            print(f"[garmin] gear 저장 실패 {g_id}: {e}")

        first_gear_id = first_gear_id or g_id

    if first_gear_id:
        conn.execute(
            "UPDATE activity_summaries SET strava_gear_id = ? WHERE id = ?",
            (first_gear_id, activity_id),
        )
    return first_gear_id


def sync_activity_exercise_sets(
    conn: sqlite3.Connection,
    client: "Garmin",
    activity_id: int,
    source_id: str,
) -> int:
    """Garmin exerciseSets → activity_exercise_sets 저장 (근력/기타 전 종목).

    Returns:
        저장된 세트 수.
    """
    try:
        data = client.get_activity_exercise_sets(int(source_id))
    except Exception as e:
        print(f"[garmin] exercise_sets 조회 실패 {source_id}: {e}")
        return 0

    if not data:
        return 0

    sets = (
        data if isinstance(data, list)
        else data.get("exerciseSets") or data.get("sets") or []
    )
    if not sets:
        return 0

    _store_raw_payload(
        conn, "activity_exercise_sets", source_id, data, activity_id=activity_id
    )

    count = 0
    for i, s in enumerate(sets):
        etype = s.get("exerciseType") or {}
        exercise_name = (
            etype.get("typeKey") or etype.get("typeId") or s.get("exerciseName")
        )
        category = s.get("category") or etype.get("category")

        weight_raw = s.get("weight")
        weight_kg = None
        if weight_raw is not None:
            try:
                weight_kg = float(weight_raw)
            except (TypeError, ValueError):
                pass

        try:
            conn.execute(
                """INSERT INTO activity_exercise_sets
                   (activity_id, source, set_index, exercise_name, exercise_category,
                    set_type, reps, weight_kg, duration_sec, distance_m)
                   VALUES (?, 'garmin', ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(activity_id, source, set_index) DO UPDATE SET
                       exercise_name = excluded.exercise_name,
                       exercise_category = excluded.exercise_category,
                       set_type = excluded.set_type,
                       reps = excluded.reps,
                       weight_kg = excluded.weight_kg,
                       duration_sec = excluded.duration_sec,
                       distance_m = excluded.distance_m""",
                (
                    activity_id, s.get("setOrder", i), exercise_name, category,
                    s.get("setType"), s.get("reps"), weight_kg,
                    s.get("duration"), s.get("distance"),
                ),
            )
            count += 1
        except sqlite3.Error as e:
            print(f"[garmin] exercise_set 저장 실패 {source_id} idx {i}: {e}")

    return count


def sync_activity_weather(
    conn: sqlite3.Connection,
    client: "Garmin",
    activity_id: int,
    source_id: str,
) -> None:
    """Garmin 활동 날씨 데이터 → activity_detail_metrics 저장."""
    try:
        data = client.get_activity_weather(source_id)
    except Exception as e:
        print(f"[garmin] activity_weather 조회 실패 {source_id}: {e}")
        return

    if not data:
        return

    _store_raw_payload(conn, "activity_weather", source_id, data, activity_id=activity_id)

    weather = data if isinstance(data, dict) else {}
    metrics = {
        "weather_temp_c": weather.get("temperature"),
        "weather_dew_point_c": weather.get("dewPoint"),
        "weather_humidity_pct": weather.get("relativeHumidity"),
        "weather_wind_speed_ms": weather.get("windSpeed"),
        "weather_wind_direction_deg": weather.get("windDirection"),
        "weather_precipitation_pct": weather.get("precipProbability"),
        "weather_apparent_temp_c": weather.get("apparentTemperature"),
    }
    for name, value in metrics.items():
        if value is not None:
            try:
                conn.execute(
                    """INSERT OR IGNORE INTO activity_detail_metrics
                       (activity_id, source, metric_name, metric_value)
                       VALUES (?, 'garmin', ?, ?)""",
                    (activity_id, name, float(value)),
                )
            except (sqlite3.Error, TypeError, ValueError):
                pass

    # 날씨 조건 문자열 저장
    condition = weather.get("weatherType") or weather.get("weatherTypeName")
    if condition:
        try:
            conn.execute(
                """INSERT OR IGNORE INTO activity_detail_metrics
                   (activity_id, source, metric_name, metric_json)
                   VALUES (?, 'garmin', 'weather_condition', ?)""",
                (activity_id, json.dumps({"value": condition})),
            )
        except sqlite3.Error:
            pass


def sync_activity_hr_zones(
    conn: sqlite3.Connection,
    client: "Garmin",
    activity_id: int,
    source_id: str,
) -> None:
    """Garmin 활동별 HR 구간 분포 → activity_detail_metrics 저장."""
    try:
        data = client.get_activity_hr_in_timezones(source_id)
    except Exception as e:
        print(f"[garmin] hr_in_timezones 조회 실패 {source_id}: {e}")
        return

    if not data:
        return

    _store_raw_payload(conn, "activity_hr_zones", source_id, data, activity_id=activity_id)

    zones = data if isinstance(data, list) else data.get("zones") or []
    for zone in zones:
        zone_num = zone.get("zoneNumber") or zone.get("zone")
        seconds = zone.get("secsInZone") or zone.get("secondsInZone")
        if zone_num is not None and seconds is not None:
            try:
                conn.execute(
                    """INSERT OR IGNORE INTO activity_detail_metrics
                       (activity_id, source, metric_name, metric_value)
                       VALUES (?, 'garmin', ?, ?)""",
                    (activity_id, f"hr_zone_{zone_num}_sec", float(seconds)),
                )
            except (sqlite3.Error, TypeError, ValueError):
                pass

    if zones:
        try:
            conn.execute(
                """INSERT OR IGNORE INTO activity_detail_metrics
                   (activity_id, source, metric_name, metric_json)
                   VALUES (?, 'garmin', 'hr_zones_detail', ?)""",
                (activity_id, json.dumps(zones)),
            )
        except sqlite3.Error:
            pass


def sync_activity_power_zones(
    conn: sqlite3.Connection,
    client: "Garmin",
    activity_id: int,
    source_id: str,
) -> None:
    """Garmin 활동별 power 구간 분포 → activity_detail_metrics 저장."""
    try:
        data = client.get_activity_power_in_timezones(source_id)
    except Exception as e:
        print(f"[garmin] power_in_timezones 조회 실패 {source_id}: {e}")
        return

    if not data:
        return

    _store_raw_payload(conn, "activity_power_zones", source_id, data, activity_id=activity_id)

    zones = data if isinstance(data, list) else data.get("zones") or []
    for zone in zones:
        zone_num = zone.get("zoneNumber") or zone.get("zone")
        seconds = zone.get("secsInZone") or zone.get("secondsInZone")
        if zone_num is not None and seconds is not None:
            try:
                conn.execute(
                    """INSERT OR IGNORE INTO activity_detail_metrics
                       (activity_id, source, metric_name, metric_value)
                       VALUES (?, 'garmin', ?, ?)""",
                    (activity_id, f"power_zone_{zone_num}_sec", float(seconds)),
                )
            except (sqlite3.Error, TypeError, ValueError):
                pass

    if zones:
        try:
            conn.execute(
                """INSERT OR IGNORE INTO activity_detail_metrics
                   (activity_id, source, metric_name, metric_json)
                   VALUES (?, 'garmin', 'power_zones_detail', ?)""",
                (activity_id, json.dumps(zones)),
            )
        except sqlite3.Error:
            pass
