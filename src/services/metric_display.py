"""메트릭 표시 메타 — API가 내려주는 format·decimal_places·higher_is_better (21 design §7.2)."""
from __future__ import annotations

from src.utils.metric_labels import label_for

_UNIT_FORMAT = {"sec": "duration", "sec/km": "pace", "%": "percent", "score": "score"}
_NAME_FORMAT = {
    "tsb": "signed",
    "race_pred_5k_sec": "race_time",
    "race_pred_10k_sec": "race_time",
    "race_pred_half_sec": "race_time",
    "race_pred_marathon_sec": "race_time",
}
_INT_UNITS = {"bpm", "ms", "W", "count", "kcal", "score", "brpm", "min/wk", "%"}
_UNIT_MIN_SPAN = {"bpm": 5.0, "sec/km": 10.0, "score": 10.0, "ratio": 0.2}
_RACE_TIME_MIN_SPAN_PCT = 0.02  # 예측 기록은 값의 2%
HIGHER_IS_BETTER: dict[str, bool | None] = {
    "tsb": True, "ctl": None, "atl": None, "utrs": True, "cirs": False, "rri": True,
}


def display_name(name: str, description: str) -> tuple[str, str | None]:
    """(name_ko, abbr) — metric_labels SSOT, 미등록은 폴백."""
    label = label_for(name, description)
    return label.name_ko, label.abbr


def min_span(fmt: str, unit: str, value: float | None) -> float | None:
    """스파크라인 y 범위 최소 폭(21 design §5). 기준이 없는 단위는 None."""
    if fmt == "race_time":
        return round(abs(value) * _RACE_TIME_MIN_SPAN_PCT, 1) if value else None
    return _UNIT_MIN_SPAN.get(unit)


def display_meta(name: str, unit: str, description: str = "", value: float | None = None) -> dict:
    """name_ko·abbr + format·decimal_places·higher_is_better·min_span(스파크라인 최소 y 폭)."""
    name_ko, abbr = display_name(name, description or name)
    fmt = _NAME_FORMAT.get(name) or _UNIT_FORMAT.get(unit, "number")
    return {
        "name_ko": name_ko,
        "abbr": abbr,
        "format": fmt,
        "decimal_places": 0 if fmt in ("race_time", "duration", "pace", "signed") or unit in _INT_UNITS else 1,
        "higher_is_better": HIGHER_IS_BETTER.get(name),
        "min_span": min_span(fmt, unit, value),
    }
