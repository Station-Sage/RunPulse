"""계획 행 → 세그먼트 구조(structure_json, 순수) — 거리뿐 아니라 세트 수·반복 거리·구간 페이스로 이행을 판정하기 위한 기준.

형식은 outcome_v2 docstring 참고. 추가 키(연속 러닝 work 단계):
  max_only  True 면 "이보다 빠르면 안 됨"만 본다(이지·회복·롱런 — Daniels E 는 상한 속도).
  min_share 목표 페이스에 들어와야 하는 거리 비중(이지·롱 0.8, 템포 0.4 — 워밍업·쿨다운 포함 거리 대비).
"""
from __future__ import annotations

import json

WU_S = CD_S = 600.0
_SHARE = {"easy": 0.8, "recovery": 0.8, "long": 0.8, "tempo": 0.4}


def _speeds(pace_min: float | None, pace_max: float | None) -> dict:
    """페이스 범위(초/km, min=빠른 쪽) → speed_lo/hi(m/s)."""
    if not pace_min and not pace_max:
        return {}
    fast, slow = pace_min or pace_max, pace_max or pace_min
    return {"speed_lo": round(1000.0 / slow, 4), "speed_hi": round(1000.0 / fast, 4)}


def structure_for_plan(workout_type: str, distance_km: float | None, pace_min: float | None,
                       pace_max: float | None, interval_prescription: str | dict | None = None) -> dict | None:
    """planner 가 만든 행의 세그먼트 구조. 만들 수 없으면 None(휴식·대회·정보 부족)."""
    if workout_type in ("rest", "race"):
        return None
    if workout_type == "interval":
        rx = json.loads(interval_prescription) if isinstance(interval_prescription, str) else interval_prescription
        if not rx or not rx.get("sets") or not rx.get("rep_m") or not rx.get("interval_pace"):
            return None
        sp = _speeds(rx["interval_pace"], rx["interval_pace"])
        rep = {"type": "repeat", "count": int(rx["sets"]), "steps": [
            {"type": "work", "dist_m": float(rx["rep_m"]), **sp},
            {"type": "rest", "dur_s": float(rx.get("rest_sec") or 0)}]}
        return {"steps": [{"type": "warmup", "dur_s": WU_S}, rep, {"type": "cooldown", "dur_s": CD_S}]}
    if not distance_km:
        return None
    step = {"type": "work", "dist_m": round(distance_km * 1000.0, 1), **_speeds(pace_min, pace_max),
            "min_share": _SHARE.get(workout_type, 0.8)}
    if workout_type != "tempo":
        step["max_only"] = True          # 이지·회복·롱런: 느린 쪽은 허용, 빠른 쪽만 위반
    return {"steps": [step]}
