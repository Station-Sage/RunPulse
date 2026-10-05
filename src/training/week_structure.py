"""주간 구조 규칙 R7(순수) — 러닝 일수 기본값, 롱런 상한, 최소 세션 병합·재분배 (DESIGN-U16 §2.3).

DB를 읽지 않는다. 입력은 주간 행 리스트(dict: date, workout_type, distance_km, target_pace_min …)이고
규칙 적용 결과로 새 리스트를 돌려준다(입력 불변).
"""
from __future__ import annotations

import statistics
from datetime import date, timedelta

MIN_SESSION_KM, MIN_SESSION_MIN = 6.0, 35.0
LONG_MAX_MIN, LONG_MAX_KM = 150.0, 32.0
R_DEFAULT, R_HIGH, R_HIGH_WEEK_KM = 0.35, 0.45, 60.0
EASY_FILL_MAX_KM = 12.0
SHAKEOUT_MAX_KM = 5.0
_LONG = ("long", "long_mp")
_FILL = ("easy", "recovery")
_SKIP = ("rest", "race")


def default_run_days(per_week_days: list[int]) -> int:
    """최근 주별 러닝 일수의 중앙값을 3~6으로 자른다. 기록이 없으면 4."""
    vals = [d for d in per_week_days if d > 0]
    if not vals:
        return 4
    return max(3, min(6, round(statistics.median(vals))))


def long_ratio(week_km: float, long_max_12w: float) -> float:
    """롱런 상한 비율 r. 주 60km 미만이면서 최근 12주 최장이 0.45×주간 km 이상이면 0.45."""
    if week_km < R_HIGH_WEEK_KM and long_max_12w >= R_HIGH * week_km:
        return R_HIGH
    return R_DEFAULT


def long_cap_km(week_km: float, long_pace_sec: float, long_max_12w: float = 0.0) -> float:
    """롱런 상한 = min(r×주간 km, 150분÷롱런 페이스, 32km)."""
    by_time = LONG_MAX_MIN * 60.0 / long_pace_sec if long_pace_sec > 0 else LONG_MAX_KM
    return min(long_ratio(week_km, long_max_12w) * week_km, by_time, LONG_MAX_KM)


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
    for kinds, limit in ((_FILL, EASY_FILL_MAX_KM), (_LONG, cap_long)):
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
                         long_max_12w: float = 0.0, race_date: str | None = None) -> list[dict]:
    """R7 적용: 러닝 일수 초과 병합, 롱런 상한 절단, 최소 세션 미달을 휴식으로 합쳐 이지일에 재분배한다."""
    out = [dict(r) for r in rows]
    cap = long_cap_km(week_km, long_pace_sec, long_max_12w)
    pool = 0.0
    for r in out:
        if r["workout_type"] in _LONG and float(r.get("distance_km") or 0.0) > cap:
            pool += float(r["distance_km"]) - cap
            r["distance_km"] = round(cap, 1)
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
    _distribute(out, pool, cap)
    return out
