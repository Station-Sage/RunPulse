"""활동 유형 정규화.

각 소스의 activity type 문자열을 RunPulse 내부 표준으로 변환합니다.
"""

from __future__ import annotations

_RUNNING_TYPES = {
    "running", "run", "trail_running", "trail_run", "treadmill_running",
    "treadmill", "track_running", "virtual_run", "race", "road_running",
}

_CYCLING_TYPES = {
    "cycling", "road_cycling", "mountain_biking", "virtual_ride",
    "gravel_cycling", "indoor_cycling", "ride", "virtualride",
}

_SWIMMING_TYPES = {
    "swimming", "pool_swimming", "open_water_swimming", "swim",
    "lap_swimming",
}

_WALKING_TYPES = {
    "walking", "walk", "hiking", "hike",
}

_STRENGTH_TYPES = {
    "strength_training", "strength", "weight_training",
}

_TYPE_MAP: dict[str, str] = {}
for _t in _RUNNING_TYPES:
    _TYPE_MAP[_t] = "running"
for _t in _CYCLING_TYPES:
    _TYPE_MAP[_t] = "cycling"
for _t in _SWIMMING_TYPES:
    _TYPE_MAP[_t] = "swimming"
for _t in _WALKING_TYPES:
    _TYPE_MAP[_t] = "walking"
for _t in _STRENGTH_TYPES:
    _TYPE_MAP[_t] = "strength"

# Strava 특수 매핑
_STRAVA_MAP = {
    "Run": "running",
    "TrailRun": "running",
    "VirtualRun": "running",
    "Ride": "cycling",
    "VirtualRide": "cycling",
    "Swim": "swimming",
    "Walk": "walking",
    "Hike": "walking",
    "WeightTraining": "strength",
}

# Intervals.icu 특수 매핑
_INTERVALS_MAP = {
    "Run": "running",
    "Ride": "cycling",
    "Swim": "swimming",
    "Walk": "walking",
    "WeightTraining": "strength",
    "VirtualRun": "running",
    "VirtualRide": "cycling",
    "TrailRun": "running",
}


def normalize_activity_type(raw_type: str, source: str | None = None) -> str:
    """소스별 activity type을 정규화된 문자열로 변환.

    Returns: 'running', 'cycling', 'swimming', 'walking', 'strength', 또는 원본(소문자).
    """
    if not raw_type:
        return "unknown"

    # 소스 전용 매핑 먼저
    if source == "strava" and raw_type in _STRAVA_MAP:
        return _STRAVA_MAP[raw_type]
    if source == "intervals" and raw_type in _INTERVALS_MAP:
        return _INTERVALS_MAP[raw_type]

    key = raw_type.lower().strip()
    return _TYPE_MAP.get(key, key)
