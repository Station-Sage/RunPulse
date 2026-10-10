"""품질 세션 사다리 처방 적용(순수, E8) — 사다리 단계(progression.py)를 v2 주간 행의 interval·tempo·long_mp 처방에 덮어쓴다.

행의 거리(주간 합계)는 바꾸지 않는다. 처방이 행 거리에 들어가지 않으면 그 행은 v1 처방을 그대로 둔다.
"""
from __future__ import annotations

import json

from . import progression as PG
from .plan_structure import WU_S, CD_S, _speeds, structure_for_plan

WUCD_KM = 3.0          # 워밍업·쿨다운 10분씩 ≈ 3km
TEMPO_REST_S = 90.0    # 템포 반복 사이 조깅 휴식
_TEMPO_MIN_SHARE = 0.4


def long_mp_structure(r: dict, mp: float) -> dict | None:
    """long_mp 행: 앞 이지 구간 + 뒤 MP 구간."""
    easy_km = max(0.0, float(r["distance_km"]) - float(r["mp_km"]))
    easy = structure_for_plan("long", easy_km, r.get("target_pace_min"), r.get("target_pace_max")) if easy_km > 0 else None
    mps = structure_for_plan("marathon", float(r["mp_km"]), round(mp - 3), round(mp + 5))
    return {"steps": ((easy or {}).get("steps") or []) + (mps or {}).get("steps", [])}


def _note(r: dict, text: str) -> None:
    r["rationale"] = f"{r.get('rationale') or ''} {text}".strip()


def _interval(r: dict, step: int) -> bool:
    rx = json.loads(r["interval_prescription"]) if r.get("interval_prescription") else None
    if not rx or not rx.get("interval_pace"):
        return False
    p = PG.prescription("interval", step)
    if p["reps"] * p["rep_km"] + WUCD_KM > float(r.get("distance_km") or 0.0) + 1e-6:
        return False
    rx.update(sets=p["reps"], rep_m=int(round(p["rep_km"] * 1000)))
    r["interval_prescription"] = json.dumps(rx, ensure_ascii=False)
    r["structure"] = structure_for_plan("interval", r.get("distance_km"), None, None, rx)
    _note(r, f"품질 사다리 {step + 1}단계: {p['reps']}×{int(rx['rep_m'])}m.")
    return True


def _tempo(r: dict, step: int) -> bool:
    pmin, pmax = r.get("target_pace_min"), r.get("target_pace_max")
    dist = float(r.get("distance_km") or 0.0)
    if not pmin or not dist:
        return False
    p = PG.prescription("tempo", step)
    if "continuous_min" in p:
        work_km = p["continuous_min"] * 60.0 / ((pmin + (pmax or pmin)) / 2.0)
        if work_km + WUCD_KM > dist + 1e-6:
            return False
        st = structure_for_plan("tempo", dist, pmin, pmax)
        st["steps"][0]["min_share"] = round(min(1.0, max(_TEMPO_MIN_SHARE, work_km / dist)), 3)
        r["structure"] = st
        _note(r, f"품질 사다리 {step + 1}단계: 연속 {p['continuous_min']}분.")
        return True
    if p["reps"] * p["rep_km"] + WUCD_KM > dist + 1e-6:
        return False
    sp = _speeds(pmin, pmax)
    rep = {"type": "repeat", "count": p["reps"], "steps": [
        {"type": "work", "dist_m": round(p["rep_km"] * 1000.0, 1), **sp},
        {"type": "rest", "dur_s": TEMPO_REST_S}]}
    r["structure"] = {"steps": [{"type": "warmup", "dur_s": WU_S}, rep, {"type": "cooldown", "dur_s": CD_S}]}
    _note(r, f"품질 사다리 {step + 1}단계: {p['reps']}×{p['rep_km']:g}km.")
    return True


def _long_mp(r: dict, step: int, mp: float | None, floor_km: float) -> bool:
    cur = float(r.get("mp_km") or 0.0)
    if not mp or not cur:
        return False
    new = min(cur, max(PG.prescription("long_mp", step)["mp_km"], floor_km))
    if abs(new - cur) < 1e-6:
        return False
    r["mp_km"] = new
    r["structure"] = long_mp_structure(r, mp)
    _note(r, f"품질 사다리 {step + 1}단계: MP {new:.0f}km.")
    return True


def apply_ladder(rows: list[dict], steps: dict[str, int], mp_floor_km: float = 8.0) -> list[dict]:
    """rows 의 interval·tempo·long_mp 행에 사다리 처방을 덮어쓴 새 리스트(입력 불변). steps: qtype → 단계."""
    out = [dict(r) for r in rows]
    for r in out:
        t = r["workout_type"]
        if t == "interval" and "interval" in steps:
            _interval(r, steps["interval"])
        elif t == "tempo" and "tempo" in steps:
            _tempo(r, steps["tempo"])
        elif t == "long_mp" and "long_mp" in steps:
            _long_mp(r, steps["long_mp"], r.get("_mp_sec"), mp_floor_km)
    return out
