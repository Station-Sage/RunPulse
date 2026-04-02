"""활동 타입 정규화 — 소스별 다른 이름을 통일."""

# 소스별 타입 → 정규화 타입 매핑
_NORMALIZE_MAP: dict[str, str] = {
    # running
    "run": "running",
    "running": "running",
    "treadmill_running": "treadmill_running",
    "virtualrun": "treadmill_running",
    "trail_running": "trail_running",
    "trailrun": "trail_running",
    # swimming
    "swim": "swimming",
    "swimming": "swimming",
    "lap_swimming": "lap_swimming",
    "openwaterswim": "open_water_swimming",
    "open_water_swimming": "open_water_swimming",
    # strength
    "weighttraining": "strength_training",
    "strength_training": "strength_training",
    # hiit
    "hiit": "hiit",
    "highintensityintervaltraining": "hiit",
    # cycling
    "ride": "cycling",
    "cycling": "cycling",
    "virtualride": "virtual_cycling",
    # other
    "walk": "walking",
    "walking": "walking",
    "workout": "workout",
    "elliptical": "elliptical",
}


def normalize_activity_type(raw_type: str | None) -> str:
    """소스별 활동 타입을 정규화된 이름으로 변환.

    Args:
        raw_type: API에서 받은 원본 타입 (예: "Run", "run", "running").

    Returns:
        정규화된 타입. 매핑 없으면 소문자로 반환.
    """
    if not raw_type:
        return "unknown"
    key = raw_type.strip().lower()
    return _NORMALIZE_MAP.get(key, key)
