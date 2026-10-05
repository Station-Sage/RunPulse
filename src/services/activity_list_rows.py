"""활동 목록 행 부가 필드 — workout_class·display_title·load·is_race (UX 리뷰 20 §7-2 ④).

읽기 전용. metric_store에서 페이지 단위로 한 번씩만 조회한다.
"""
from __future__ import annotations

import re
import sqlite3

from src.metrics.workout_classifier import TAG_LABELS
from src.services.activity_feedback_service import feedback_for_activities
from src.services.activity_list_filters import TYPE_CLASSES

_CLASS_TO_KEY = {v: k for k, vals in TYPE_CLASSES.items() for v in vals}
_GENERIC_NAME = re.compile(
    r"^\s*((아침|오전|점심|오후|저녁|야간|morning|afternoon|lunch|evening|night)\s*)?(달리기|러닝|run|running)\s*$",
    re.IGNORECASE)


def is_generic_name(name: str | None) -> bool:
    return not name or bool(_GENERIC_NAME.match(name))


def display_title(name: str | None, label: str | None, distance_m: float | None) -> str | None:
    """기본 이름이면 '이지런 9.3km'처럼 유형·거리로 대체, 사용자가 붙인 이름은 그대로."""
    if not is_generic_name(name):
        return name
    if not label or not distance_m:
        return name
    return f"{label} {distance_m / 1000:.1f}km"


def _fetch(conn: sqlite3.Connection, ids: list[int], metric: str, col: str, provider_like: str) -> dict[int, object]:
    out: dict[int, object] = {}
    marks = ",".join("?" * len(ids))
    for sid, val in conn.execute(
        f"SELECT scope_id, {col} FROM metric_store WHERE scope_type='activity' AND metric_name=?"
        f" AND provider LIKE ? AND {col} IS NOT NULL AND scope_id IN ({marks})",
        [metric, provider_like, *[str(i) for i in ids]]):
        out.setdefault(int(sid), val)
    return out


def enrich_rows(conn: sqlite3.Connection, activities: list[dict]) -> None:
    """각 행에 workout_class(API 키), workout_label, display_title, load, is_race, rpe를 추가(제자리)."""
    if not activities:
        return
    ids = [a["id"] for a in activities]
    classes = _fetch(conn, ids, "workout_type_classified", "text_value", "runpulse%")
    loads = _fetch(conn, ids, "hrss", "numeric_value", "runpulse%")
    feedbacks = feedback_for_activities(conn, ids)
    for a in activities:
        fb = feedbacks.get(a["id"])
        a["rpe"] = fb["rpe"] if fb else None
        key = _CLASS_TO_KEY.get(classes.get(a["id"]))
        label = TAG_LABELS.get(key) if key else None
        load = loads.get(a["id"])
        a["workout_class"] = key
        a["workout_label"] = label
        a["display_title"] = display_title(a.get("name"), label, a.get("distance_m"))
        a["load"] = round(float(load), 1) if load is not None else None
        a["is_race"] = key == "race"
