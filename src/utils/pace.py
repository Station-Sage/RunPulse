"""페이스 변환 유틸리티 (초 ↔ 분:초, km/h ↔ min/km)."""


def seconds_to_pace(seconds: int) -> str:
    """초를 'M:SS' 페이스 문자열로 변환.

    Args:
        seconds: sec/km 값.

    Returns:
        "M:SS" 형식 문자열 (예: 300 → "5:00").
    """
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes}:{secs:02d}"


def pace_to_seconds(pace_str: str) -> int:
    """'M:SS' 페이스 문자열을 초로 변환.

    Args:
        pace_str: "M:SS" 형식 문자열.

    Returns:
        sec/km 정수값 (예: "5:00" → 300).
    """
    parts = pace_str.split(":")
    return int(parts[0]) * 60 + int(parts[1])


def kmh_to_pace(kmh: float) -> int:
    """km/h 속도를 sec/km 페이스로 변환.

    Args:
        kmh: 시속 (km/h).

    Returns:
        sec/km 정수값 (예: 12.0 → 300).
    """
    if kmh <= 0:
        raise ValueError(f"속도는 0보다 커야 합니다: {kmh}")
    return round(3600 / kmh)


def pace_to_kmh(sec_per_km: int) -> float:
    """sec/km 페이스를 km/h 속도로 변환.

    Args:
        sec_per_km: 킬로미터당 초.

    Returns:
        km/h 소수점 1자리 (예: 300 → 12.0).
    """
    if sec_per_km <= 0:
        raise ValueError(f"페이스는 0보다 커야 합니다: {sec_per_km}")
    return round(3600 / sec_per_km, 1)


def format_duration(seconds: int) -> str:
    """초를 'H:MM:SS' 또는 'M:SS' 형식으로 변환.

    Args:
        seconds: 총 시간 (초).

    Returns:
        1시간 이상이면 "H:MM:SS", 미만이면 "M:SS".
    """
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"
