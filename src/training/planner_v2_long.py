"""계획 규칙 v2 롱런 후처리 — 예산(§5.1)으로 러닝 일수·롱런 거리를 정하고 주간 합계를 보존해 재분배한다.

DESIGN-U16-LONGRUN §5. 순수 함수(DB 무접근)이며 행 리스트를 제자리에서 바꾼다(planner_v2.apply_v2 가 복사본을 넘긴다).
"""
from __future__ import annotations

from dataclasses import replace
from datetime import date

from . import long_run_rules as LR
from .planner_rules import description
from .week_structure import EASY_FILL_MAX_KM, MIN_SESSION_KM, spill

_FILL = ("easy", "recovery")
_Q = ("tempo", "interval", "marathon")
_LONG = ("long", "long_mp")
_SKIP = ("rest", "race")
LEGACY_LONG_FLOOR = MIN_SESSION_KM + 1.0      # 문맥 없이 부를 때의 롱런 바닥(기존 값)
TOL = 0.05


def total(rows: list[dict]) -> float:
    return sum(float(r.get("distance_km") or 0.0) for r in rows if r["workout_type"] != "race")


def _km(r: dict) -> float:
    return float(r.get("distance_km") or 0.0)


def _shrink(rows: list[dict], delta: float, floor_of) -> float:
    """긴 세션부터 floor_of(r)까지 줄여 delta(<0)를 흡수한다. 남은 delta를 돌려준다."""
    for r in sorted(rows, key=lambda x: -_km(x)):
        if delta >= -TOL:
            break
        cur = _km(r)
        new = max(cur + delta, floor_of(r))
        if new < cur:
            r["distance_km"] = round(new, 1)
            delta -= round(new, 1) - cur
    return delta


def rebalance(rows: list[dict], target: float, fixed_date: str | None = None, long_floor: float = LEGACY_LONG_FLOOR,
              long_fill: float | None = None, long_cap: float | None = None) -> None:
    """주간 합계를 target 에 맞춘다(제자리, 버리지 않음). fixed_date 행(대회 전날 쉐이크아웃)은 건드리지 않는다.

    줄일 때: 이지(6km까지) → 롱런(long_floor, MP 구간+3km까지) → 퀄리티/MP(6km, MP 구간+3km까지).
    늘릴 때: 이지(12km까지) → 롱런(long_fill까지) → 퀄리티/MP → 롱런(long_cap까지) → 이지.
    """
    easy = [r for r in rows if r["workout_type"] in _FILL and r["date"] != fixed_date]
    delta = target - total(rows)
    for r in sorted(easy, key=lambda x: -_km(x) if delta < 0 else _km(x)):
        if abs(delta) < TOL:
            return
        cur = _km(r)
        new = round(min(EASY_FILL_MAX_KM, cur + delta) if delta > 0 else max(MIN_SESSION_KM, cur + delta), 1)
        r["distance_km"] = new
        delta -= new - cur
    if delta < -TOL:
        mp_floor = lambda r: float(r.get("mp_km") or 0.0) + 3.0 if r.get("mp_km") else 0.0  # noqa: E731
        delta = _shrink([r for r in rows if r["workout_type"] in _LONG], delta, lambda r: max(long_floor, mp_floor(r)))
        _shrink([r for r in rows if r["workout_type"] in _Q], delta, lambda r: max(MIN_SESSION_KM, mp_floor(r)))
        return
    if delta > TOL and long_fill is not None:
        for r in (x for x in rows if x["workout_type"] in _LONG):
            add = min(delta, max(0.0, long_fill - _km(r)))
            r["distance_km"] = round(_km(r) + add, 1)
            delta -= add
    if delta > TOL:
        cap = long_cap if long_cap is not None else max((_km(r) for r in rows if r["workout_type"] in _LONG), default=0.0)
        spill([r for r in rows if r["date"] != fixed_date], delta, cap)


def trim_run_days(rows: list[dict], n: int) -> None:
    """러닝 행이 n개를 넘으면 짧은 이지/회복 → 퀄리티 순으로 휴식으로 바꾼다(롱런 유지). km는 rebalance 가 되살린다."""
    run = [r for r in rows if r["workout_type"] not in _SKIP]
    order = sorted((r for r in run if r["workout_type"] in _FILL), key=_km) + [r for r in run if r["workout_type"] in _Q]
    for r in order[:max(0, len(run) - n)]:
        r.update(workout_type="rest", distance_km=0.0, description=description("rest", 0.0, date.fromisoformat(r["date"])))


def plan_long_week(out: list[dict], *, dlabel: str, phase: str, weeks_to_race: int, week_km: float, run_days: int,
                   long_pace_sec: float, long6: float, long12: float, taper_first: bool,
                   mp_week: bool) -> tuple[LR.LongCtx | None, int, bool]:
    """롱런 주에 §5.1 예산을 적용한다(제자리). (기록할 문맥 | None, 러닝 일수, MP를 롱런 안에 담는지)."""
    longs = [r for r in out if r["workout_type"] == "long"]
    if not longs:
        return None, run_days, False
    sched = _km(longs[0])
    ctx0 = LR.LongCtx(dlabel, phase, weeks_to_race, week_km, run_days, long_pace_sec, sched, long6, long12, taper_first)
    b = LR.plan_long_budget(ctx0, mp_week)
    if not b.has_long:     # 저볼륨 주 — 이름만 롱런인 짧은 세션 대신 이지로
        start = LR.min_viable_week_km(dlabel, 2)
        for r in longs:
            r.update(workout_type="easy", description=description("easy", _km(r), date.fromisoformat(r["date"])),
                     rationale=f"주간 볼륨이 롱런을 담기에 작다 — 볼륨이 {start:.0f}km를 넘는 주부터 롱런 시작.")
        return None, b.run_days, False
    ctx = replace(ctx0, run_days=b.run_days, mp_extra_km=b.mp_extra_km)
    km = max(LR.budget_floor_km(ctx), min(sched, LR.long_cap_km(ctx)))
    for r in longs:
        r["distance_km"] = round(km, 1)
    return ctx, b.run_days, b.mp_in_long


def long_fill_km(ctx: LR.LongCtx) -> float:
    """남는 km를 롱런에 채울 천장 = min(상한, max(스케줄 롱런, basis)) — 스케줄보다 길게 늘리지 않는다."""
    return min(LR.long_cap_km(ctx), max(ctx.sched_long_km, LR.basis_km(ctx)))
