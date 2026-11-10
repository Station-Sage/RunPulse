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
# M-10: 단위 없는 0~100 점수는 정수, 부하비 계열은 소수 2자리(목록·상세·차트 공통)
_SCORE_NAMES = frozenset({"utrs", "cirs", "crs", "rri", "sleep_score", "body_battery_high", "body_battery_low",
                          "avg_stress", "training_readiness_score", "sleep_body_battery_change"})
_RATIO_NAMES = frozenset({"acwr", "lsi", "monotony", "ramp_rate"})
_UNIT_MIN_SPAN = {"bpm": 5.0, "sec/km": 10.0, "score": 10.0, "ratio": 0.2}
_RACE_TIME_MIN_SPAN_PCT = 0.02  # 예측 기록은 값의 2%
HIGHER_IS_BETTER: dict[str, bool | None] = {
    "tsb": True, "ctl": None, "atl": None, "utrs": True, "cirs": False, "rri": True,
}


def display_name(name: str, description: str) -> tuple[str, str | None]:
    """(name_ko, abbr) — metric_labels SSOT, 미등록은 폴백."""
    label = label_for(name, description)
    return label.name_ko, label.abbr


def action_hint(name: str, status: str | None, level: int | None = None,
                assertive: bool = True, boost_hold: bool = False) -> str | None:
    """현재 status(crs는 게이트 level)에 맞는 행동 힌트 1문장. 문구가 없으면 None.

    crs 는 신선도가 단정 불가(assertive=False)면 힌트를 내지 않고, BOOST 보류(boost_hold)면
    level 4(부스트)를 level 3 문구로 낮춘다.
    """
    hints = label_for(name).action_hint
    if not hints:
        return None
    if name != "crs":
        return hints.get(status) if status else None
    if level is None or not assertive:
        return None
    if boost_hold and level >= 4:
        level = 3
    return hints.get(f"level_{level}")


def min_span(fmt: str, unit: str, value: float | None) -> float | None:
    """스파크라인 y 범위 최소 폭(21 design §5). 기준이 없는 단위는 None."""
    if fmt == "race_time":
        return round(abs(value) * _RACE_TIME_MIN_SPAN_PCT, 1) if value else None
    return _UNIT_MIN_SPAN.get(unit)


def _format_of(name: str, unit: str) -> str:
    """registry 단위·이름 → 표시 형식. 수면·스트레스 시간은 '7h 18m'(duration_hm, M-21 웰니스 화면과 같음)."""
    if name in _NAME_FORMAT:
        return _NAME_FORMAT[name]
    if unit == "sec" and name.startswith(("sleep_", "stress_")):
        return "duration_hm"
    if not unit and name in _SCORE_NAMES:
        return "score"
    return _UNIT_FORMAT.get(unit, "number")


def _decimals(name: str, fmt: str, unit: str) -> int:
    if fmt in ("race_time", "duration", "duration_hm", "pace", "signed", "score") or unit in _INT_UNITS:
        return 0
    return 2 if name in _RATIO_NAMES else 1


def display_meta(name: str, unit: str, description: str = "", value: float | None = None) -> dict:
    """name_ko·abbr + format·decimal_places·higher_is_better·min_span(스파크라인 최소 y 폭)."""
    name_ko, abbr = display_name(name, description or name)
    fmt = _format_of(name, unit)
    return {
        "name_ko": name_ko,
        "abbr": abbr,
        "description_short": label_for(name).description_short,
        "format": fmt,
        "decimal_places": _decimals(name, fmt, unit),
        "higher_is_better": HIGHER_IS_BETTER.get(name),
        "min_span": min_span(fmt, unit, value),
    }
