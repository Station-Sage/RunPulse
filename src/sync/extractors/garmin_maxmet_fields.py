"""Garmin maxmet/daily 응답 → 일별 VO2max(소수 1자리) MetricRecord 변환."""
from __future__ import annotations

from src.sync.extractors.base import MetricRecord


def _num(v) -> float | None:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    return float(v) if v > 0 else None


def extract_vo2max_daily(extractor, items) -> dict[str, list[MetricRecord]]:
    """maxmet/daily list → {날짜: [vo2max MetricRecord]}. 정밀값이 없으면 정수값으로 폴백."""
    out: dict[str, list[MetricRecord]] = {}
    if not isinstance(items, list):
        return out
    for item in items:
        generic = item.get("generic") if isinstance(item, dict) else None
        if not isinstance(generic, dict):
            continue
        day = str(generic.get("calendarDate") or "")[:10]
        precise = _num(generic.get("vo2MaxPreciseValue"))
        integer = _num(generic.get("vo2MaxValue"))
        value = precise if precise is not None else integer
        if len(day) != 10 or value is None:
            continue
        rec = extractor._metric(
            "vo2max", round(value, 1),
            json_val={"int": integer, "max_met_category": generic.get("maxMetCategory")},
            raw_name="vo2MaxPreciseValue" if precise is not None else "vo2MaxValue",
        )
        if rec is not None:
            out[day] = [rec]
    return out
