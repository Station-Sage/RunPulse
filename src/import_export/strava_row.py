"""Strava activities.csv 행 파싱 — 활동 유형 매핑·숫자/날짜 헬퍼·행 정규화 (strava_csv 하위 모듈).

`_parse_strava_date` 는 UTC 를 KST(+9h) 로 옮긴 임시값을 돌려주고, 실제 현지 벽시계는
`strava_tz.resolve_strava_start` 체인이 결정한다 (TZ T2). 원본 UTC 는 `start_date_utc` 로 보존한다.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

_LOCAL_UTC_OFFSET = timedelta(hours=9)

# ── Strava 활동 유형 → 내부 유형 ─────────────────────────────────────────
_TYPE_MAP: dict[str, str] = {
    "Run": "running",
    "Walk": "walking",
    "Hike": "hiking",
    "Swim": "swimming",
    "Ride": "cycling",
    "VirtualRide": "cycling",
    "VirtualRun": "running",
    "WeightTraining": "strength",
    "Weight Training": "strength",
    "Workout": "workout",
    "Elliptical": "elliptical",
    "Yoga": "yoga",
    "HIIT": "hiit",
}


# ── 파싱 헬퍼 ────────────────────────────────────────────────────────────

def _clean(v: str | None) -> str | None:
    if v is None:
        return None
    v = v.strip()
    return None if v == "" else v


def _float(v: str | None) -> float | None:
    v = _clean(v)
    if v is None:
        return None
    try:
        return float(v)
    except ValueError:
        return None


def _int(v: str | None) -> int | None:
    f = _float(v)
    return int(f) if f is not None else None


_DATE_FORMATS = ("%b %d, %Y, %I:%M:%S %p", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%SZ")


def parse_strava_utc(v: str | None) -> datetime | None:
    """CSV 'Activity Date' (UTC) → naive UTC datetime. 파싱 불가면 None."""
    v = (v or "").strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(v, fmt)
        except ValueError:
            continue
    return None


def _parse_strava_date(v: str) -> str | None:
    """CSV UTC → KST(+9h) 임시 ISO 문자열 (실제 현지 시각은 strava_tz 체인이 결정)."""
    v = (v or "").strip()
    if not v:
        return None
    dt = parse_strava_utc(v)
    return (dt + _LOCAL_UTC_OFFSET).isoformat() if dt else v


def _speed_to_pace(speed_m_s: float | None) -> int | None:
    """m/s → sec/km."""
    if not speed_m_s or speed_m_s <= 0:
        return None
    return int(1000 / speed_m_s)


def _parse_activity_row(row: dict[str, str]) -> dict[str, Any]:
    """activities.csv 단일 행 → 정규화된 dict."""
    activity_type_raw = _clean(row.get("Activity Type")) or "Run"
    activity_type = _TYPE_MAP.get(activity_type_raw, activity_type_raw.lower())

    start_time = _parse_strava_date(row.get("Activity Date", ""))
    distance_m = _float(row.get("Distance"))
    distance_km = distance_m / 1000 if distance_m else None

    moving_time_sec = _int(row.get("Moving Time"))
    elapsed_time_sec = _int(row.get("Elapsed Time"))
    duration_sec = moving_time_sec or elapsed_time_sec

    avg_speed = _float(row.get("Average Speed"))
    avg_pace_sec_km = _speed_to_pace(avg_speed)

    # pace가 없으면 distance/time으로 계산
    if avg_pace_sec_km is None and distance_km and duration_sec and distance_km > 0:
        avg_pace_sec_km = int(duration_sec / distance_km)

    return {
        "source_id": str(row.get("Activity ID", "")).strip(),
        "activity_type": activity_type,
        "start_time": start_time,
        "start_date_utc": utc.isoformat() if (utc := parse_strava_utc(row.get("Activity Date", ""))) else None,
        "description": _clean(row.get("Activity Name")),
        "activity_description": _clean(row.get("Activity Description")),
        "distance_km": distance_km,
        "duration_sec": duration_sec,
        "avg_pace_sec_km": avg_pace_sec_km,
        "avg_hr": _int(row.get("Average Heart Rate")),
        "max_hr": _int(row.get("Max Heart Rate")),
        "avg_cadence": _int(row.get("Average Cadence")),
        "elevation_gain": _float(row.get("Elevation Gain")),
        "avg_power": _int(row.get("Average Watts")),
        # 확장 필드 (raw payload + activity_detail_metrics 저장)
        "max_speed": _float(row.get("Max Speed")),
        "max_power": _int(row.get("Max Watts")),
        "elevation_loss": _float(row.get("Elevation Loss")),
        "elevation_low": _float(row.get("Elevation Low")),
        "elevation_high": _float(row.get("Elevation High")),
        "max_cadence": _int(row.get("Max Cadence")),
        "relative_effort": _float(row.get("Relative Effort")),
        "training_load": _float(row.get("Training Load")),
        "intensity": _float(row.get("Intensity")),
        "avg_grade": _float(row.get("Average Grade")),
        "grade_adjusted_distance_m": _float(row.get("Grade Adjusted Distance")),
        "avg_grade_adjusted_pace_sec_km": _int(row.get("Average Grade Adjusted Pace")),
        "total_work_joules": _float(row.get("Total Work")),
        "total_steps": _int(row.get("Total Steps")),
        "avg_temp_c": _float(row.get("Average Temperature")),
        # 날씨 데이터
        "weather_condition": _clean(row.get("Weather Condition")),
        "weather_temp_c": _float(row.get("Weather Temperature")),
        "weather_humidity": _float(row.get("Humidity")),
        "wind_speed_ms": _float(row.get("Wind Speed")),
        "wind_gust_ms": _float(row.get("Wind Gust")),
        "uv_index": _float(row.get("UV Index")),
        "cloud_cover": _float(row.get("Cloud Cover")),
        "gear": _clean(row.get("Activity Gear")),
        "filename": _clean(row.get("Filename")),
        "activity_type_raw": activity_type_raw,
        "moving_time_sec": moving_time_sec,
        "elapsed_time_sec": elapsed_time_sec,
    }
