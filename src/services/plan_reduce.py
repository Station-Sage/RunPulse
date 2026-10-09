"""행 액션 reduce/easy 의 after 계산 (순수) — 강도 세션은 세트 수·구간 거리로, 쉬운 세션은 거리 비율로 줄인다 (ADR-035, DESIGN-PLAN-ROW-ACTION-COACHING §2).

페이스는 바꾸지 않는다. 강도 세션을 줄이면 structure_json·interval_prescription 도 after 에 함께 쓴다.
거부는 ValueError(메시지) — API 가 400 으로 변환한다.
"""
from __future__ import annotations

import json

from src.training.plan_structure import structure_for_plan

MAX_REDUCE_PCT = 50
MIN_REDUCED_KM = 3.0
LONG_TO_EASY_KM = 16.0
WORK_PCTS = (20, 30)
LONG_PCTS = (15, 20, 30, 40)
MIN_WORK_KM = {"tempo": 2.0, "threshold": 2.0, "marathon": 5.0, "long_mp": 5.0}
Q_WORK = tuple(MIN_WORK_KM)
EASY_FIELDS = {"target_pace_min": None, "target_pace_max": None, "interval_prescription": None}


def _num(v, lo, hi, msg):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not lo <= v <= hi:
        raise ValueError(msg)
    return v


def _with_structure(after: dict) -> dict:
    s = structure_for_plan(after["workout_type"], after.get("distance_km"), after.get("target_pace_min"),
                           after.get("target_pace_max"), after.get("interval_prescription"))
    return {**after, "structure_json": json.dumps(s) if s else None}


def _interval(before: dict, params: dict) -> dict:
    if "pct" in params and "reps" not in params:
        raise ValueError("인터벌은 비율 대신 반복 횟수로 줄여요 (PCT_NOT_FOR_QUALITY)")
    reps = _num(params.get("reps"), 1, 2, "줄일 반복 수는 1~2 이어야 해요")
    raw = before.get("interval_prescription")
    rx = json.loads(raw) if isinstance(raw, str) else raw
    if not rx or not rx.get("sets") or not rx.get("rep_m"):
        raise ValueError("세트 구성이 없는 인터벌은 줄일 수 없어요 · 쉬운 러닝으로 바꾸거나 쉬세요 (NO_STRUCTURE)")
    sets, left = int(rx["sets"]), int(rx["sets"]) - int(reps)
    if left < 2 or left * 2 < sets:
        raise ValueError("남는 반복이 2회 미만이거나 절반 아래예요 · 쉬운 러닝으로 바꾸거나 쉬세요")
    cut_km = int(reps) * float(rx["rep_m"]) / 1000.0
    km = before.get("distance_km")
    after = {**before, "interval_prescription": json.dumps({**rx, "sets": left})}
    if km:
        after["distance_km"] = round(max(km - cut_km, MIN_REDUCED_KM), 1)
    return _with_structure(after)


def _continuous(before: dict, params: dict, wtype: str) -> dict:
    allowed = LONG_PCTS if wtype == "long" else WORK_PCTS if wtype in Q_WORK else None
    pct = _num(params.get("pct"), 1, 99, "pct 는 1~99 이어야 해요")
    if pct > MAX_REDUCE_PCT:
        raise ValueError(f"한 번에 {MAX_REDUCE_PCT}% 넘게 줄일 수 없어요 · 쉬는 날로 바꿔 보세요")
    if allowed and pct not in allowed:
        raise ValueError("가능한 비율: " + "·".join(f"{p}%" for p in allowed))
    km = before.get("distance_km")
    if not km:
        raise ValueError("거리가 없는 세션은 줄일 수 없어요 (NO_BASIS)")
    new_km = round(km * (1 - pct / 100), 1)
    floor = MIN_WORK_KM.get(wtype, MIN_REDUCED_KM)
    if new_km < floor:
        raise ValueError(f"{floor:g}km 미만으로는 줄일 수 없어요 · 쉬는 날로 바꿔 보세요 (BELOW_FLOOR)")
    after = {**before, "distance_km": new_km}
    if wtype == "long" and new_km < LONG_TO_EASY_KM:
        after["workout_type"] = "easy"
    return _with_structure(after) if wtype in (*Q_WORK, "long") else after


def reduce_after(before: dict, params: dict) -> dict:
    wtype = before.get("workout_type")
    if wtype == "interval":
        return _interval(before, params)
    if wtype == "race":
        raise ValueError("대회는 줄일 수 없어요 (RACE_FIXED)")
    return _continuous(before, params, wtype)


def easy_after(before: dict) -> dict:
    """강도·롱런 세션을 같은 거리의 이지로 대체. 페이스 목표·세트 구성은 비운다."""
    if before.get("workout_type") not in (*Q_WORK, "interval", "long"):
        raise ValueError("이미 쉬운 세션이에요")
    return _with_structure({**before, **EASY_FIELDS, "workout_type": "easy"})
