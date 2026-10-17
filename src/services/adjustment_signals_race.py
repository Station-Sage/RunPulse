"""대회 신호 race_plan 수집 (ADJ §3.4) — race_calendar 의 -14..+21일 대회를 단계(phase)로 정규화한다. 읽기 전용."""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from src.utils.reference_day import reference_today

LOOKBACK = 21
LOOKAHEAD = 14
_BY_DIST = ((15.0, 3, 2), (30.0, 7, 4))  # (거리 상한 km, taper일, recovery일), 그 위는 풀 14/7


def windows_for(prio: str, distance_km: float, taper: int | None = None, recovery: int | None = None) -> tuple[int, int]:
    """거리 기반 보호 기간(taper, recovery). B/C 는 절반 올림, 직접 지정값은 그대로 쓴다."""
    t, r = 14, 7
    for limit, tt, rr in _BY_DIST:
        if (distance_km or 0) < limit:
            t, r = tt, rr
            break
    if prio != "A":
        t, r = (t + 1) // 2, (r + 1) // 2
    return (taper if taper is not None else t, recovery if recovery is not None else r)


def phase_of(d_day: int, prio: str, taper: int | None, recovery: int | None, distance_km: float = 42.195) -> str | None:
    """d_day = race_date - day. 대회 전 taper 창, 당일, 후 recovery 창, 그 밖은 pre_taper/None."""
    if d_day == 0:
        return "race_day"
    t, r = windows_for(prio, distance_km, taper, recovery)
    if d_day > 0:
        return "taper" if d_day <= t else "pre_taper"
    return "recovery" if -d_day <= r else None


def collect_race(conn: sqlite3.Connection, day: str) -> dict | None:
    """가장 가까운 대회 1건의 race_plan 신호. 대회 없음/테이블 없음 → None."""
    d = date.fromisoformat(day)
    lo, hi = (d - timedelta(days=LOOKBACK)).isoformat(), (d + timedelta(days=LOOKAHEAD)).isoformat()
    rows = conn.execute(
        "SELECT id, race_date, distance_km, priority, adapt_choice, taper_days, recovery_days, status FROM race_calendar"
        " WHERE status IN ('planned','done') AND adapt_choice != 'no_adapt' AND race_date BETWEEN ? AND ?",
        (lo, hi)).fetchall()
    today = reference_today(conn)[0]
    best = None
    for rid, rdate, km, prio, adapt, taper, rec, status in rows:
        if status == "done" and rdate >= today:
            continue  # 확인 필요(done·대회일≥오늘)는 신호에서 제외
        dd = (date.fromisoformat(rdate) - d).days
        ph = phase_of(dd, prio, taper, rec, km)
        if ph is None or ph == "pre_taper":
            continue
        if best is None or abs(dd) < abs(best[0]):
            best = (dd, rid, rdate, km, prio, ph, adapt in ("unasked", "later"))
    if best is None:
        return None
    dd, rid, rdate, km, prio, ph, unplanned = best
    return {"signal": "race_plan", "role": "hold", "value": dd, "as_of": day, "freshness": "fresh",
            "provider": "race_calendar",
            "detail": {"race_id": rid, "race_date": rdate, "distance_km": km, "priority": prio,
                       "phase": ph, "unplanned": unplanned}}
