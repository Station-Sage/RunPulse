"""Open-Meteo 날씨 데이터 조회 및 DB 캐시 관리.

과거 데이터: https://archive-api.open-meteo.com/v1/archive
예보 데이터: https://api.open-meteo.com/v1/forecast
무료, API 키 불필요.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date, timedelta
from typing import Any

from src.utils.api import ApiError, get

_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
_HOURLY_VARS = "temperature_2m,relativehumidity_2m,windspeed_10m,precipitation,cloudcover,apparent_temperature"

# 오늘로부터 며칠 이내는 예보 API 사용 (archive 최신 지연 약 5일)
_ARCHIVE_LAG_DAYS = 7


def get_weather(
    conn: sqlite3.Connection,
    activity_date: str,
    hour: int,
    latitude: float,
    longitude: float,
) -> dict[str, Any] | None:
    """날씨 데이터 반환. DB 캐시 우선, 없으면 Open-Meteo 호출 후 저장.

    Args:
        conn: SQLite 커넥션.
        activity_date: YYYY-MM-DD 형식.
        hour: 시간 (0-23).
        latitude: 위도.
        longitude: 경도.

    Returns:
        날씨 딕셔너리 또는 None (조회 실패 시).
    """
    cached = _load_from_cache(conn, activity_date, hour, latitude, longitude)
    if cached is not None:
        return cached

    try:
        raw = _fetch_from_api(activity_date, latitude, longitude)
    except (ApiError, KeyError, IndexError, ValueError) as e:
        print(f"[Weather] 조회 실패 {activity_date} ({latitude:.3f},{longitude:.3f}): {e}")
        return None

    if not raw:
        return None

    # hour 인덱스로 데이터 추출
    hourly = raw.get("hourly", {})
    times = hourly.get("time", [])
    target = f"{activity_date}T{hour:02d}:00"

    try:
        idx = times.index(target)
    except ValueError:
        # 정확한 시간 없으면 가장 가까운 인덱스 사용
        idx = min(range(len(times)), key=lambda i: abs(int(times[i][11:13]) - hour)) if times else 0

    row = _extract_row(hourly, idx)
    _save_to_cache(conn, activity_date, hour, latitude, longitude, row)
    return row


def get_weather_for_activity(
    conn: sqlite3.Connection,
    start_time: str,
    latitude: float | None,
    longitude: float | None,
) -> dict[str, Any] | None:
    """활동 시작 시간과 위치로 날씨 조회. 좌표 없으면 None 반환.

    Args:
        conn: SQLite 커넥션.
        start_time: ISO 8601 형식 (예: '2026-03-15T07:30:00').
        latitude: 활동 위도.
        longitude: 활동 경도.

    Returns:
        날씨 딕셔너리 또는 None.
    """
    if latitude is None or longitude is None:
        return None

    parts = start_time[:19].split("T")
    if len(parts) != 2:
        return None

    activity_date = parts[0]
    hour = int(parts[1][:2])
    lat_rounded = round(latitude, 2)
    lon_rounded = round(longitude, 2)

    return get_weather(conn, activity_date, hour, lat_rounded, lon_rounded)


# ── 내부 함수 ────────────────────────────────────────────────────────────────

def _load_from_cache(
    conn: sqlite3.Connection,
    activity_date: str,
    hour: int,
    latitude: float,
    longitude: float,
) -> dict[str, Any] | None:
    """DB 캐시에서 날씨 데이터 조회."""
    row = conn.execute(
        """SELECT temp_c, feels_like_c, humidity_pct, wind_speed_ms,
                  precipitation_mm, cloudcover_pct
           FROM weather_data
           WHERE date = ? AND hour = ? AND latitude = ? AND longitude = ?""",
        (activity_date, hour, latitude, longitude),
    ).fetchone()

    if row is None:
        return None

    return {
        "temp_c": row[0],
        "feels_like_c": row[1],
        "humidity_pct": row[2],
        "wind_speed_ms": row[3],
        "precipitation_mm": row[4],
        "cloudcover_pct": row[5],
    }


def _fetch_from_api(
    activity_date: str,
    latitude: float,
    longitude: float,
) -> dict:
    """Open-Meteo API에서 날씨 데이터 조회. 과거/예보 API 자동 선택."""
    today = date.today()
    target = date.fromisoformat(activity_date)
    use_archive = target < today - timedelta(days=_ARCHIVE_LAG_DAYS)

    url = _ARCHIVE_URL if use_archive else _FORECAST_URL
    params: dict[str, Any] = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": _HOURLY_VARS,
        "start_date": activity_date,
        "end_date": activity_date,
        "timezone": "auto",
    }
    if not use_archive:
        params["past_days"] = 7

    return get(url, params=params)  # type: ignore[return-value]


def _extract_row(hourly: dict, idx: int) -> dict[str, Any]:
    """hourly 데이터에서 idx 번째 값 추출."""

    def val(key: str) -> Any:
        lst = hourly.get(key, [])
        return lst[idx] if idx < len(lst) else None

    return {
        "temp_c": val("temperature_2m"),
        "feels_like_c": val("apparent_temperature"),
        "humidity_pct": int(val("relativehumidity_2m")) if val("relativehumidity_2m") is not None else None,
        "wind_speed_ms": val("windspeed_10m"),
        "precipitation_mm": val("precipitation"),
        "cloudcover_pct": int(val("cloudcover")) if val("cloudcover") is not None else None,
    }


def _save_to_cache(
    conn: sqlite3.Connection,
    activity_date: str,
    hour: int,
    latitude: float,
    longitude: float,
    row: dict[str, Any],
) -> None:
    """날씨 데이터를 DB에 저장 (UPSERT)."""
    conn.execute(
        """INSERT INTO weather_data
               (date, hour, latitude, longitude, temp_c, feels_like_c,
                humidity_pct, wind_speed_ms, precipitation_mm, cloudcover_pct)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(date, hour, latitude, longitude)
           DO UPDATE SET
               temp_c=excluded.temp_c,
               feels_like_c=excluded.feels_like_c,
               humidity_pct=excluded.humidity_pct,
               wind_speed_ms=excluded.wind_speed_ms,
               precipitation_mm=excluded.precipitation_mm,
               cloudcover_pct=excluded.cloudcover_pct,
               fetched_at=datetime('now')""",
        (
            activity_date, hour, latitude, longitude,
            row.get("temp_c"), row.get("feels_like_c"),
            row.get("humidity_pct"), row.get("wind_speed_ms"),
            row.get("precipitation_mm"), row.get("cloudcover_pct"),
        ),
    )
    conn.commit()
