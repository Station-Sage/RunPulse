"""주간 적응 규칙(순수, DESIGN-U16 §3.4) — 지난주 이행도로 다음 주 목표 km·퀄리티 수·사다리 동결을 정한다.

DB를 읽지 않는다. 첫 번째로 맞는 규칙이 이긴다: 부상/CRS 적색 → 이행도 <0.70 → 0.70~0.90 → 정상 진행.
미이행분 보충은 하지 않고, 초과 이행(>1.15)에도 목표를 올리지 않는다.
"""
from __future__ import annotations

from dataclasses import dataclass

V_LOW, V_MID = 0.70, 0.90
Q_MIN, ACWR_MAX = 0.5, 1.3
RED_DAYS_MAX = 2
INJURY_FACTOR = 0.9
PROTECT_PHASES = ("taper", "race")


@dataclass(frozen=True)
class AdaptInput:
    volume_pct: float | None      # 지난주 볼륨 이행도(0~, 1.0=100%). None 이면 판단 불가
    quality_pct: float | None     # 지난주 퀄리티 이행도
    last_actual_km: float
    this_target_km: float         # 지난주(=이번 주 직전) 목표
    sched_next_km: float          # 일정표상 다음 주 목표
    acwr: float | None = None
    crs_red_days: int = 0
    injury_flag: bool = False
    next_phase: str = "build"


@dataclass(frozen=True)
class AdaptDecision:
    rule: str                     # injury | low | mid | proceed | no_data
    target_km: float
    max_quality: int | None       # None = 제한 없음
    freeze_ladder: bool
    rationale: str


def decide(x: AdaptInput) -> AdaptDecision:
    if x.volume_pct is None:
        return AdaptDecision("no_data", x.sched_next_km, None, False, "지난주 이행 데이터 없음 — 일정표대로.")
    if x.injury_flag or x.crs_red_days >= RED_DAYS_MAX:
        why = "부상/질병 표시" if x.injury_flag else f"CRS 적색 {x.crs_red_days}일"
        km = round(min(x.last_actual_km * INJURY_FACTOR, x.sched_next_km), 1)
        return AdaptDecision("injury", km, 1, True, f"{why} — 지난주 실제 {x.last_actual_km:.1f}km×0.9, 퀄리티 1회 이하, 사다리 동결.")
    if x.volume_pct < V_LOW:
        km = round(min(x.last_actual_km, x.sched_next_km), 1)
        return AdaptDecision("low", km, None, True, f"볼륨 이행 {x.volume_pct:.0%}<70% — 지난주 실제량 유지(보충 없음), 사다리 반복.")
    if x.volume_pct < V_MID:
        km = x.this_target_km if x.next_phase not in PROTECT_PHASES else min(x.this_target_km, x.sched_next_km)
        return AdaptDecision("mid", round(km, 1), None, True, f"볼륨 이행 {x.volume_pct:.0%}(70~90%) — 이번 주 목표 반복, 일정 1주 지연.")
    ok = (x.quality_pct is None or x.quality_pct >= Q_MIN) and (x.acwr is None or x.acwr <= ACWR_MAX)
    if ok:
        note = " 초과 이행분은 반영하지 않음." if x.volume_pct > 1.15 else ""
        return AdaptDecision("proceed", x.sched_next_km, None, False, f"볼륨 이행 {x.volume_pct:.0%} — 일정표대로 진행.{note}")
    why = "ACWR>1.3" if x.acwr is not None and x.acwr > ACWR_MAX else "퀄리티 이행<50%"
    km = x.this_target_km if x.next_phase not in PROTECT_PHASES else min(x.this_target_km, x.sched_next_km)
    return AdaptDecision("mid", round(km, 1), None, True, f"{why} — 이번 주 목표 반복, 사다리 반복.")


def apply_to_rows(rows: list[dict], d: AdaptDecision, sched_km: float) -> list[dict]:
    """일정표 기준으로 만든 주간 행을 결정에 맞게 비례 축소/정리(입력 불변). 목표가 일정표 이상이면 km는 그대로."""
    out = [dict(r) for r in rows]
    if d.max_quality is not None:
        q = [r for r in out if r["workout_type"] in ("tempo", "interval", "marathon")]
        for r in q[d.max_quality:]:
            r["workout_type"], r["interval_prescription"], r["structure"] = "easy", None, None
            r["description"] = "이지런(퀄리티 제한)"
    total = sum(float(r.get("distance_km") or 0.0) for r in out if r["workout_type"] not in ("rest", "race"))
    if sched_km > 0 and d.target_km < sched_km and total > 0:
        f = d.target_km / sched_km
        for r in out:
            if r["workout_type"] not in ("rest", "race") and r.get("distance_km"):
                r["distance_km"] = round(float(r["distance_km"]) * f, 1)
    for r in out:
        if r["workout_type"] not in ("rest", "race"):
            r["rationale"] = (r.get("rationale") or "") + f" [주간 적응: {d.rationale}]"
    return out
