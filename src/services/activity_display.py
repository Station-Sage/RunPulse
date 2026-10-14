"""활동 표시 계약 — 스포츠 군별로 보일 거리·페이스·시간·대체 셀 결정 (ADR-051 NRA-3/4/5)."""
from __future__ import annotations

from src.utils.activity_types import SPORT_LABELS, sport_family

_PACE_FAMILIES = {"running": ("/km", 1000.0), "walking": ("/km", 1000.0), "swimming": ("/100m", 100.0)}
_NO_DISTANCE = {"strength", "other"}


def _sec(v) -> int | None:
    return int(v) if isinstance(v, (int, float)) and v > 0 else None


def build_display(core: dict, sets: int | None = None) -> dict:
    """core 한 건 → 표시 계약. 기존 core 키는 건드리지 않고 별도 dict 로 반환."""
    family = sport_family(core.get("activity_type"), core.get("source"))
    dist = core.get("distance_m") or 0
    elapsed = _sec(core.get("elapsed_time_sec")) or _sec(core.get("duration_sec"))
    moving = _sec(core.get("moving_time_sec"))
    basis = "moving" if moving else "elapsed"
    moving = moving or elapsed
    show_distance = family not in _NO_DISTANCE and dist > 0
    pace, speed = None, None
    if show_distance and moving:
        if family in _PACE_FAMILIES:
            unit, per = _PACE_FAMILIES[family]
            pace = {"value_sec": round(moving / dist * per, 1), "unit": unit, "basis": basis}
        elif family == "cycling":
            speed = round(dist / moving * 3.6, 1)
    alt = []
    for key, val in (("duration", elapsed), ("avg_hr", core.get("avg_hr")),
                     ("calories", core.get("calories")), ("sets", sets)):
        if val:
            alt.append({"key": key, "value": val})
    return {"family": family, "label": SPORT_LABELS.get(family, "기타"), "show_distance": show_distance,
            "pace": pace, "speed_kmh": speed, "times": {"moving_sec": moving, "elapsed_sec": elapsed},
            "alt_fields": alt}
