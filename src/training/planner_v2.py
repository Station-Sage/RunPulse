"""계획 규칙 v2 후처리(DESIGN-U16) — v1 주간 행에 MP 세션·롱런 페이스·주간 구조 규칙을 입힌다.

generate_weekly_plan 이 rules_version>=2 인 목표에서 호출한다. 순수 함수(DB 무접근)이며 입력 행을 바꾸지 않는다.
"""
from __future__ import annotations

from datetime import date, timedelta

from . import marathon_rules as MR
from .plan_structure import structure_for_plan
from .week_structure import EASY_FILL_MAX_KM, MIN_SESSION_KM, apply_week_structure

_Q = ("tempo", "interval")
_NAMES = {"marathon": "마라톤 페이스런", "long_mp": "롱런(MP 구간)"}
_DAYS = "월화수목금토일"
SHAKEOUT_KM = 4.0         # 대회 전날 조깅(G3 면제, week_structure.SHAKEOUT_MAX_KM 이하)
MP_SESSION_KM = 8.0       # G4 하한. 워밍업·쿨다운 포함 총거리는 +3km


def _total(rows: list[dict]) -> float:
    return sum(float(r.get("distance_km") or 0.0) for r in rows if r["workout_type"] != "race")


def _rebalance(rows: list[dict], target: float, fixed_date: str | None = None) -> None:
    """이지/회복 행에서 합계 차이를 흡수해 주간 총거리를 target 에 맞춘다(제자리). fixed_date 행(대회 전날 쉐이크아웃)은 건드리지 않는다."""
    easy = [r for r in rows if r["workout_type"] in ("easy", "recovery") and r["date"] != fixed_date]
    delta = target - _total(rows)
    for r in sorted(easy, key=lambda x: -(x.get("distance_km") or 0.0) if delta < 0 else (x.get("distance_km") or 0.0)):
        if abs(delta) < 0.05:
            return
        cur = float(r.get("distance_km") or 0.0)
        new = min(EASY_FILL_MAX_KM, cur + delta) if delta > 0 else max(MIN_SESSION_KM, cur + delta)
        r["distance_km"] = round(new, 1)
        delta -= new - cur
    if delta < -0.05:     # 이지가 최소 길이에 닿으면 롱런을 바닥(최소 세션+1km, MP 구간 포함 시 mp_km+3km)까지 줄인다
        for r in sorted((x for x in rows if x["workout_type"] in ("long", "long_mp")), key=lambda x: -(x.get("distance_km") or 0.0)):
            cur = float(r.get("distance_km") or 0.0)
            new = max(cur + delta, MIN_SESSION_KM + 1.0, float(r.get("mp_km") or 0.0) + 3.0)
            if new < cur:
                r["distance_km"] = round(new, 1)
                delta -= new - cur
    if delta > 0.05:      # 이지가 상한에 닿으면 MP 세션이 나머지를 흡수한다
        for r in rows:
            if r["workout_type"] == "marathon":
                r["distance_km"] = round(float(r.get("distance_km") or 0.0) + delta, 1)
                return


def _retype(r: dict, wtype: str, km: float, mp_km: float, mp: float) -> None:
    pmin, pmax = round(mp - 3), round(mp + 5)
    d = date.fromisoformat(r["date"])
    r.update(workout_type=wtype, distance_km=round(km, 1), mp_km=mp_km, target_pace_min=pmin, target_pace_max=pmax,
             interval_prescription=None, description=f"{_DAYS[d.weekday()]}요일 {km:.1f}km {_NAMES[wtype]}",
             rationale=f"마라톤 페이스 {mp_km:.0f}km 포함 — 목표 페이스 체득.",
             structure=structure_for_plan(wtype, km, pmin, pmax))


def _mp_session(rows: list[dict], mp: float, mp_km: float) -> bool:
    """Q-day(없으면 이지 중 가장 긴 날) 하나를 MP 세션으로 바꾼다."""
    cand = [r for r in rows if r["workout_type"] in _Q] or [r for r in rows if r["workout_type"] == "easy"]
    if not cand:
        return False
    r = max(cand, key=lambda x: float(x.get("distance_km") or 0.0))
    _retype(r, "marathon", max(float(r.get("distance_km") or 0.0), mp_km + 3.0), mp_km, mp)
    return True


def _race_week(rows: list[dict], mp: float, race_date: str) -> None:
    """대회 주: 대회 3일 전 이전의 러닝일 하나를 MP 3~5km 세션으로(총 6km 이상)."""
    sess = MR.race_week_session()
    race = date.fromisoformat(race_date)
    cand = [r for r in rows if r["workout_type"] not in ("rest", "race")
            and (race - date.fromisoformat(r["date"])).days >= 3]
    if cand:
        r = cand[len(cand) // 2]
        _retype(r, "marathon", sess["distance_km"], sess["mp_km"], mp)


def _shakeout(rows: list[dict], race_date: str | None) -> str | None:
    """대회 전날 러닝 행이 있으면 SHAKEOUT_KM 로 줄인다. 그 날짜를 돌려준다."""
    if not race_date:
        return None
    eve = (date.fromisoformat(race_date) - timedelta(days=1)).isoformat()
    for r in rows:
        if r["date"] == eve and r["workout_type"] in ("easy", "recovery"):
            r["distance_km"] = SHAKEOUT_KM
            return eve
    return None


def apply_v2(rows: list[dict], *, dlabel: str, phase: str, weeks_to_race: int, taper_first: bool, mp_now: float | None,
             mp_goal: float | None, weeks_since_build: int, run_days: int, week_km: float, long_max_12w: float,
             race_date: str | None) -> list[dict]:
    """v1 행 → v2 행. MP 세션은 풀마라톤 build~taper1·대회 주에만 넣는다."""
    out = [dict(r) for r in rows]
    if race_date:     # 대회일 이후·대회 당일 행은 구조 규칙이 km를 배분하지 않도록 미리 비운다
        for r in out:
            if r["date"] >= race_date:
                r.update(workout_type="race" if r["date"] == race_date else "rest", distance_km=0.0)
        run_days = sum(1 for r in out if r["workout_type"] not in ("rest", "race"))
    mp = MR.prescribed_mp(mp_now, mp_goal, weeks_since_build)
    mp_week = dlabel == "full" and mp is not None and (phase in ("build", "peak") or (phase == "taper" and taper_first))
    if weeks_to_race > 0 or phase != "taper":     # 세션 최소 길이(+MP 세션 추가분)를 못 채우는 주는 러닝일을 줄인다
        while run_days > 2 and run_days * MIN_SESSION_KM + 1.0 + (MP_SESSION_KM - MIN_SESSION_KM + 3 if mp_week else 0) > week_km + 0.5:
            run_days -= 1
    if phase == "taper" and weeks_to_race == 0 and race_date:     # 대회 주: 전날 조깅 외 예산이 작으면 러닝일을 줄인다
        eve_d = (date.fromisoformat(race_date) - timedelta(days=1)).isoformat()
        runs = [r for r in out if r["workout_type"] not in ("rest", "race") and r["date"] != eve_d]
        for r in runs[max(1, int((week_km - SHAKEOUT_KM) // MIN_SESSION_KM)):]:
            r.update(workout_type="rest", distance_km=0.0)
        run_days = sum(1 for r in out if r["workout_type"] not in ("rest", "race"))
    target = week_km
    for r in out:     # 퀄리티 세션이 최소 길이 미만이면 구조 규칙이 휴식으로 지워 버리므로 미리 끌어올린다
        short_ok = r["workout_type"] in ("easy", "recovery") and not (phase == "taper" and weeks_to_race == 0)
        if (r["workout_type"] in _Q or short_ok) and 0 < float(r.get("distance_km") or 0.0) < MIN_SESSION_KM:
            r["distance_km"] = MIN_SESSION_KM
    if mp is not None:
        for r in out:
            r["_mp_sec"] = mp
            if r["workout_type"] == "long":
                lp = MR.long_run_pace(mp)
                r["target_pace_min"], r["target_pace_max"] = round(lp - 10), round(lp + 10)
    if mp is not None and dlabel == "full":
        longs = [r for r in out if r["workout_type"] == "long"]
        if phase in ("build", "peak") and longs:
            lg = longs[0]
            km = float(lg.get("distance_km") or 0.0)
            mpk = MR.long_mp_km(km, phase)
            if mpk >= MP_SESSION_KM:
                lg.update(workout_type="long_mp", mp_km=mpk)
            elif phase in ("build", "peak") and _mp_session(out, mp, MP_SESSION_KM):
                lg.update(workout_type="long_mp", mp_km=mpk)
        elif phase in ("build", "peak"):
            _mp_session(out, mp, MP_SESSION_KM)
        elif phase == "taper" and taper_first:
            n_other = max(0, sum(1 for r in out if r["workout_type"] not in ("rest", "race")) - 1)
            fit = week_km - n_other * MIN_SESSION_KM - 3.0
            _mp_session(out, mp, max(MP_SESSION_KM, min(MR.taper_week1_mp_km(max(12.0, week_km * 0.3)), fit)))
        elif phase == "taper" and weeks_to_race == 0 and race_date:
            _race_week(out, mp, race_date)
    eve = _shakeout(out, race_date) if phase == "taper" and weeks_to_race == 0 else None
    _rebalance(out, target, eve)
    lp = MR.long_run_pace(mp) if mp else 360.0
    res = apply_week_structure(out, run_days, week_km, lp, long_max_12w, race_date)
    if _total(res) > week_km + 0.05:     # 롱런 절단 뒤 이지 재분배가 목표를 넘기면 이지에서 되돌린다
        _rebalance(res, week_km, eve)
    return res


def apply_for_goal(conn, goal: dict, rows: list[dict], target, dlabel: str, paces: dict, week_start: date,
                   n_run_days: int, vdot: float | None = None, as_of: date | None = None) -> list[dict]:
    """DB 문맥(목표·주기화 일정·최근 롱런)을 모아 apply_v2 를 호출한다. target 이 없으면 rows 그대로."""
    from .planner_schedule import schedule_for_goal, recent_load
    if target is None:
        return rows
    sched = schedule_for_goal(conn, goal, dlabel, vdot, as_of)
    tapers = [t.weeks_to_race for t in sched if t.phase == "taper"]
    taper_first = bool(tapers) and target.phase == "taper" and target.weeks_to_race == max(tapers)
    secs = goal.get("target_time_sec")
    mp_goal = goal.get("target_pace_sec_km") or (secs / 42.195 if secs and dlabel == "full" else None)
    _, long_max = recent_load(conn, min(week_start, as_of) if as_of else week_start)
    return apply_v2(rows, dlabel=dlabel, phase=target.phase, weeks_to_race=target.weeks_to_race,
                    taper_first=taper_first, mp_now=paces.get("M"), mp_goal=mp_goal,
                    weeks_since_build=max(0, 16 - target.weeks_to_race), run_days=n_run_days,
                    week_km=target.weekly_km, long_max_12w=long_max, race_date=goal.get("race_date"))
