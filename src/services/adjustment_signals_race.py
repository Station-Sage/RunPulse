"""대회 신호 race_plan 수집 (ADJ §3.4) — race_calendar 의 -14..+21일 대회를 단계(phase)로 정규화한다. 읽기 전용."""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

TAPER = {"A": 14, "B": 7, "C": 3}
RECOVERY = {"A": 7, "B": 4, "C": 2}
LOOKBACK = 21
LOOKAHEAD = 14


def _window(prio: str, override: int | None, table: dict) -> int:
    if override is not None:
        return override
    return table[prio]


def phase_of(d_day: int, prio: str, taper: int | None, recovery: int | None) -> str | None:
    """d_day = race_date - day. 대회 전 taper 창, 당일, 후 recovery 창, 그 밖은 pre_taper/None."""
    if d_day == 0:
        return "race_day"
    if d_day > 0:
        return "taper" if d_day <= _window(prio, taper, TAPER) else "pre_taper"
    return "recovery" if -d_day <= _window(prio, recovery, RECOVERY) else None


def collect_race(conn: sqlite3.Connection, day: str) -> dict | None:
    """가장 가까운 대회 1건의 race_plan 신호. 대회 없음/테이블 없음 → None."""
    d = date.fromisoformat(day)
    lo, hi = (d - timedelta(days=LOOKBACK)).isoformat(), (d + timedelta(days=LOOKAHEAD)).isoformat()
    rows = conn.execute(
        "SELECT id, race_date, distance_km, priority, adapt_choice, taper_days, recovery_days FROM race_calendar"
        " WHERE status IN ('planned','done') AND adapt_choice != 'no_adapt' AND race_date BETWEEN ? AND ?",
        (lo, hi)).fetchall()
    best = None
    for rid, rdate, km, prio, adapt, taper, rec in rows:
        dd = (date.fromisoformat(rdate) - d).days
        ph = phase_of(dd, prio, taper, rec)
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
