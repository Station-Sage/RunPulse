"""메트릭 표시 메타 — API가 내려주는 format·decimal_places·higher_is_better (21 design §7.2)."""
from __future__ import annotations

import re

_UNIT_FORMAT = {"sec": "duration", "sec/km": "pace", "%": "percent", "score": "score"}
_NAME_FORMAT = {
    "tsb": "signed",
    "race_pred_5k_sec": "race_time",
    "race_pred_10k_sec": "race_time",
    "race_pred_half_sec": "race_time",
    "race_pred_marathon_sec": "race_time",
}
_INT_UNITS = {"bpm", "ms", "W", "count", "kcal", "score", "brpm", "min/wk", "%"}
HIGHER_IS_BETTER: dict[str, bool | None] = {
    "tsb": True, "ctl": None, "atl": None, "utrs": True, "cirs": False, "rri": True,
}

_NAMES: dict[str, tuple[str, str]] = {
    "ctl": ("체력", "CTL"), "atl": ("피로", "ATL"), "tsb": ("폼", "TSB"),
    "acwr": ("급성/만성 부하비", "ACWR"), "utrs": ("훈련 준비도", "UTRS"),
    "cirs": ("부상 위험도", "CIRS"), "crs": ("복합 준비도", "CRS"), "rec": ("러닝 효율", "REC"),
}


def display_name(name: str, description: str) -> tuple[str, str | None]:
    """(name_ko, abbr). 내부 식별자 '(parent: xxx)'는 제거한다."""
    if name in _NAMES:
        return _NAMES[name]
    return re.sub(r"\s*\(parent:[^)]*\)", "", description).strip(), None


def display_meta(name: str, unit: str, description: str = "") -> dict:
    """name_ko·abbr + format(race_time/duration/pace/signed/percent/score/number)·decimal_places·higher_is_better."""
    name_ko, abbr = display_name(name, description or name)
    fmt = _NAME_FORMAT.get(name) or _UNIT_FORMAT.get(unit, "number")
    return {
        "name_ko": name_ko,
        "abbr": abbr,
        "format": fmt,
        "decimal_places": 0 if fmt in ("race_time", "duration", "pace", "signed") or unit in _INT_UNITS else 1,
        "higher_is_better": HIGHER_IS_BETTER.get(name),
    }
