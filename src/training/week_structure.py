"""주간 구조 규칙 R7(순수) — 러닝 일수 기본값, 롱런 상한, 최소 세션 병합·재분배 (DESIGN-U16 §2.3).

DB를 읽지 않는다. 입력은 주간 행 리스트(dict: date, workout_type, distance_km, target_pace_min …)이고
규칙 적용 결과로 새 리스트를 돌려준다(입력 불변). 롱런 상한은 long_run_rules 의 얇은 래퍼이고,
재분배는 주간 합계를 보존한다(남는 km를 버리지 않음, DESIGN-U16-LONGRUN D-LR-4).
"""
from __future__ import annotations

import statistics
from datetime import date, timedelta

from . import long_run_rules as LR

MIN_SESSION_KM, MIN_SESSION_MIN = 6.0, 35.0
EASY_FILL_MAX_KM = 12.0
SHAKEOUT_MAX_KM = 5.0
_LONG = ("long", "long_mp")
_FILL = ("easy", "recovery")
_QUAL = ("marathon", "tempo", "interval")
_SKIP = ("rest", "race")


def default_run_days(per_week_days: list[int]) -> int:
    """최근 주별 러닝 일수의 중앙값을 3~6으로 자른다. 기록이 없으면 4."""
    vals = [d for d in per_week_days if d > 0]
    if not vals:
        return 4
    return max(3, min(6, round(statistics.median(vals))))


def default_ctx(week_km: float, long_pace_sec: float, long_max_12w: float = 0.0, run_days: int = 0,
                sched_long_km: float = 0.0, dlabel: str = "full", phase: str = "base") -> LR.LongCtx:
    """문맥 없이 부르는 호출(단위 테스트·래퍼)의 기본 문맥 — 풀 base, 일수 미지정이면 일수 항 없음."""
    return LR.LongCtx(dlabel, phase, 8, week_km, run_days, long_pace_sec, sched_long_km, 0.0, long_max_12w)


def long_ratio(week_km: float, long_max_12w: float, **kw) -> float:
    """롱런 비중 r(long_run_rules.share_ratio 래퍼). 기본 문맥에서는 0.35, 주 60km 미만·12주 최장 ≥ 0.45×주간이면 0.45."""
    return LR.share_ratio(default_ctx(week_km, 360.0, long_max_12w, **kw))


def long_cap_km(week_km: float, long_pace_sec: float, long_max_12w: float = 0.0, **kw) -> float:
    """롱런 상한(long_run_rules.long_cap_km 래퍼). kw: run_days, sched_long_km, dlabel, phase."""
    return LR.long_cap_km(default_ctx(week_km, long_pace_sec, long_max_12w, **kw))


def feasible_week_km(run_days: int, long_pace_sec: float = 360.0, dlabel: str = "full") -> float:
    """러닝 일수로 소화 가능한 주간 최대 km(long_run_rules.feasible_week_km 래퍼, D-LR-8 B)."""
    return LR.feasible_week_km(dlabel, run_days, long_pace_sec)


def _too_short(r: dict) -> bool:
    km = float(r.get("distance_km") or 0.0)
    pace = r.get("target_pace_min")
    minutes = km * pace / 60.0 if pace else 0.0
    return km < MIN_SESSION_KM and minutes < MIN_SESSION_MIN


def _is_shakeout(r: dict, race_date: str | None) -> bool:
    if not race_date or float(r.get("distance_km") or 0.0) > SHAKEOUT_MAX_KM:
        return False
    return r.get("date") == (date.fromisoformat(race_date) - timedelta(days=1)).isoformat()


def _to_rest(r: dict) -> dict:
    return {**r, "workout_type": "rest", "distance_km": 0.0}


def _distribute(rows: list[dict], pool: float, cap_long: float) -> float:
    """pool(km)을 이지/회복 → 롱런 순으로 채운다(이지는 세션당 12km까지). 남은 양을 돌려준다."""
    return _fill(rows, pool, ((_FILL, EASY_FILL_MAX_KM), (_LONG, cap_long)))


def _fill(rows: list[dict], pool: float, steps) -> float:
    """steps = ((유형들, 세션 상한), …) 순서로 짧은 세션부터 pool 을 채운다. 남은 양을 돌려준다."""
    for kinds, limit in steps:
        for r in sorted((x for x in rows if x["workout_type"] in kinds),
                        key=lambda x: float(x.get("distance_km") or 0.0)):
            if pool <= 0:
                return 0.0
            cur = float(r.get("distance_km") or 0.0)
            add = min(pool, max(0.0, limit - cur))
            r["distance_km"] = round(cur + add, 1)
            pool -= add
    return pool


def apply_week_structure(rows: list[dict], run_days: int, week_km: float, long_pace_sec: float,
                         long_max_12w: float = 0.0, race_date: str | None = None, ctx: LR.LongCtx | None = None,
                         long_fill_km: float | None = None) -> list[dict]:
    """R7 적용: 러닝 일수 초과 병합, 롱런 상한 절단, 최소 세션 미달을 휴식으로 합쳐 재분배한다(합계 보존).

    ctx: 엔진 문맥(없으면 default_ctx). long_fill_km: 남는 km를 롱런에 채울 때의 천장(기본 = 상한).
    """
    out = [dict(r) for r in rows]
    if ctx is None:
        sched = max((float(r.get("distance_km") or 0.0) for r in out if r["workout_type"] in _LONG), default=0.0)
        ctx = default_ctx(week_km, long_pace_sec, long_max_12w, run_days, sched)
    cap = LR.long_cap_km(ctx)
    fill = cap if long_fill_km is None else min(cap, long_fill_km)
    pool = 0.0
    for r in out:
        if r["workout_type"] in _LONG and float(r.get("distance_km") or 0.0) > cap:
            pool += float(r["distance_km"]) - cap
            r["distance_km"] = round(cap, 1)
    while True:     # 가장 짧은 미달 세션부터 하나씩 휴식으로 합치고 재분배 — 남은 세션이 최소 길이를 채울 수 있게
        short = [r for r in out if r["workout_type"] in _FILL and _too_short(r) and not _is_shakeout(r, race_date)]
        if not short:
            break
        r = min(short, key=lambda x: float(x.get("distance_km") or 0.0))
        pool += float(r.get("distance_km") or 0.0)
        out[out.index(r)] = _to_rest(r)
        pool = _distribute(out, pool, fill)
    for i, r in enumerate(out):
        if r["workout_type"] not in _SKIP and _too_short(r) and not _is_shakeout(r, race_date):
            pool += float(r.get("distance_km") or 0.0)
            out[i] = _to_rest(r)
    running = [r for r in out if r["workout_type"] not in _SKIP]
    surplus = len(running) - run_days
    for r in sorted((x for x in running if x["workout_type"] in _FILL),
                    key=lambda x: float(x.get("distance_km") or 0.0))[:max(0, surplus)]:
        pool += float(r.get("distance_km") or 0.0)
        out[out.index(r)] = _to_rest(r)
    pool = _distribute(out, pool, fill)
    spill(out, pool, cap)
    return out


def spill(rows: list[dict], pool: float, cap_long: float) -> float:
    """이지·롱런 천장을 채우고도 남은 km: 퀄리티/MP → 롱런(상한까지) → 이지(상한 없이) 순으로 담는다. 버리지 않는다."""
    big = 1e9
    return _fill(rows, pool, ((_QUAL, big), (_LONG, cap_long), (_FILL, big)))
