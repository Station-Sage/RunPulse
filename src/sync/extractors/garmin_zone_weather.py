"""Garmin /hrTimeInZones·/weather 실제 응답 → 메트릭 변환 (단위 변환 포함).

hrTimeInZones: [{zoneNumber, secsInZone, zoneLowBoundary}, ...]
weather: {temp(°F), dewPoint(°F), relativeHumidity(%), windSpeed(mph), windDirection(deg), ...}
"""

from __future__ import annotations

_MPH_TO_MS = 0.44704


def f_to_c(v):
    return None if v is None else round((float(v) - 32.0) * 5.0 / 9.0, 1)


def mph_to_ms(v):
    return None if v is None else round(float(v) * _MPH_TO_MS, 2)


def hr_zone_seconds(zones) -> list[float | None]:
    """zoneNumber 순서대로 5개 존의 초. 없는 존은 None."""
    out: list[float | None] = [None] * 5
    if not isinstance(zones, list):
        return out
    for z in zones:
        if not isinstance(z, dict):
            continue
        n, secs = z.get("zoneNumber"), z.get("secsInZone")
        if isinstance(n, int) and 1 <= n <= 5 and secs is not None:
            out[n - 1] = float(secs)
    return out


def weather_values(w) -> dict[str, float | None]:
    """Garmin 날씨 → {metric_name: SI 값}. 측정 없는 응답(실내 등)은 빈 dict."""
    if not isinstance(w, dict) or w.get("temp") is None:
        return {}
    return {
        "weather_temp_c": f_to_c(w.get("temp")),
        "weather_dew_point_c": f_to_c(w.get("dewPoint")),
        "weather_humidity_pct": w.get("relativeHumidity"),
        "weather_wind_speed_ms": mph_to_ms(w.get("windSpeed")),
        "weather_wind_direction_deg": w.get("windDirection"),
    }
