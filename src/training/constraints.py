"""주간 제약 규칙(순수) — 폭염 보정·차단일 재분배·B 레이스 미니 테이퍼·교차훈련 대체 (DESIGN-U16 §3.5).

DB를 읽지 않는다. 입력은 주간 행 리스트(dict: date, workout_type, distance_km, target_pace_min/max …)이고
결과는 새 리스트(입력 불변)다. 차단일 재분배는 이지 세션당 12km 상한을 지키고 넘치는 km는 버린다.
"""
from __future__ import annotations

from datetime import date, timedelta

from . import week_structure as WS

HEAT_MIN_PCT = 2.0
B_RACE_VOLUME = 0.8
_QUAL = ("tempo", "interval", "marathon")
_SKIP = ("rest", "race")


def _km(r: dict) -> float:
    return float(r.get("distance_km") or 0.0)


def heat_adjust(rows: list[dict], heat_pct: dict[str, float]) -> list[dict]:
    """날짜별 폭염 보정(%) > 2 이면 거리는 두고 페이스 범위만 늦춘다. 퀄리티가 더 더운 날이면 가장 선선한 이지 날과 맞바꾼다."""
    out = [dict(r) for r in rows]
    runs = [r for r in out if r["workout_type"] not in _SKIP]
    for q in [r for r in runs if r["workout_type"] in _QUAL]:
        cool = [r for r in runs if r["workout_type"] in ("easy", "recovery")
                and heat_pct.get(r["date"], 0.0) < heat_pct.get(q["date"], 0.0)]
        if heat_pct.get(q["date"], 0.0) > HEAT_MIN_PCT and cool:
            c = min(cool, key=lambda r: heat_pct.get(r["date"], 0.0))
            q["date"], c["date"] = c["date"], q["date"]
    for r in runs:
        pct = heat_pct.get(r["date"], 0.0)
        if pct <= HEAT_MIN_PCT:
            continue
        for k in ("target_pace_min", "target_pace_max"):
            if r.get(k):
                r[k] = round(r[k] * (1 + pct / 100.0), 1)
        r["rationale"] = f"{r.get('rationale') or ''} [폭염 보정 +{pct:.1f}%: 페이스만 완화]".strip()
    return sorted(out, key=lambda r: r["date"])


def redistribute_blocked(rows: list[dict], blocked: set[str]) -> list[dict]:
    """차단일의 러닝을 휴식으로 바꾸고 km를 남은 이지/회복에 채운다(세션당 12km 상한, 초과분은 버림)."""
    out = [dict(r) for r in rows]
    pool = 0.0
    for i, r in enumerate(out):
        if r["date"] in blocked and r["workout_type"] not in _SKIP:
            pool += _km(r)
            out[i] = WS._to_rest(r)
    if pool > 0:
        WS._fill(out, pool, ((WS._FILL, WS.EASY_FILL_MAX_KM),))
    return out


def b_race_week(rows: list[dict], b_race_date: str, distance_km: float) -> list[dict]:
    """B 레이스 주: 볼륨 0.8배, 레이스 전 2일은 이지, 롱런을 레이스로 교체(레이스 이후 요일은 휴식)."""
    rd = date.fromisoformat(b_race_date)
    pre = {(rd - timedelta(days=n)).isoformat() for n in (1, 2)}
    out = []
    for r in rows:
        r = dict(r)
        if r["workout_type"] not in _SKIP:
            r["distance_km"] = round(_km(r) * B_RACE_VOLUME, 1)
            if r["date"] in pre and r["workout_type"] != "rest":
                r.update(workout_type="easy", interval_prescription=None)
        out.append(r)
    for r in out:
        if r["date"] == b_race_date:
            r.update(workout_type="race", distance_km=round(distance_km, 1), target_pace_min=None,
                     target_pace_max=None, interval_prescription=None, description=f"B 대회 {distance_km:.1f}km",
                     rationale="B 레이스: 미니 테이퍼")
        elif r["date"] > b_race_date and r["workout_type"] != "rest":
            r.update(WS._to_rest(r))
    return out


def cross_substituted(planned: list[dict], cross_dates: set[str]) -> set[str]:
    """교차훈련 활동이 있고 러닝이 없던 계획 러닝일 — 볼륨 이행률 분모에서 빼는 날짜 집합."""
    return {r["date"] for r in planned
            if r["workout_type"] not in _SKIP and r["date"] in cross_dates and not r.get("matched_activity_id")}
