"""활동 상세 임팩트 — CTL Δ·유사 활동 비교·레이스 맥락.

읽기 전용. DB 쓰기 없음.
첫 번째 인자는 sqlite3.Connection.
반환값은 dict 또는 None (러닝 계열 활동만 지원).
"""
from __future__ import annotations

import sqlite3
from datetime import date as _date


def get_activity_impact(
    conn: sqlite3.Connection,
    activity_id: int,
    today: _date | None = None,
) -> dict | None:
    """활동이 훈련 부하·동류 활동·레이스 맥락에서 어디에 위치하는지 반환.

    러닝 계열(activity_type LIKE '%running%')이 아니거나 거리가 없으면 None.
    반환: {"ctl_delta", "tsb", "similar", "race"}.
    """
    conn.row_factory = sqlite3.Row

    act = conn.execute(
        "SELECT id, activity_type, start_time, distance_m, avg_pace_sec_km, avg_hr"
        " FROM activity_summaries WHERE id = ?",
        (activity_id,),
    ).fetchone()

    if act is None:
        return None

    act_type: str = act["activity_type"] or ""
    if "running" not in act_type.lower():
        return None

    if not act["distance_m"]:
        return None

    act_date = str(act["start_time"])[:10]  # YYYY-MM-DD
    act_start_time = str(act["start_time"])

    ctl_delta, tsb = _load_metrics(conn, act_date)
    similar = _similar_activities(
        conn, act_start_time, act_type, act["distance_m"], act["avg_pace_sec_km"]
    )
    _today = today or _date.today()
    race = _nearest_race(conn, _today.isoformat())

    return {
        "ctl_delta": ctl_delta,
        "tsb": tsb,
        "similar": similar,
        "race": race,
    }


def _load_metrics(
    conn: sqlite3.Connection, act_date: str
) -> tuple[float | None, float | None]:
    """당일 CTL delta(전날 대비)와 TSB. 없으면 None."""
    today_ctl_row = conn.execute(
        "SELECT numeric_value FROM metric_store"
        " WHERE scope_type = 'daily' AND metric_name = 'ctl'"
        "   AND is_primary = 1 AND scope_id = ?",
        (act_date,),
    ).fetchone()

    prev_ctl_row = conn.execute(
        "SELECT numeric_value FROM metric_store"
        " WHERE scope_type = 'daily' AND metric_name = 'ctl'"
        "   AND is_primary = 1 AND scope_id < ?"
        " ORDER BY scope_id DESC LIMIT 1",
        (act_date,),
    ).fetchone()

    ctl_delta: float | None = None
    today_ctl = today_ctl_row["numeric_value"] if today_ctl_row else None
    prev_ctl = prev_ctl_row["numeric_value"] if prev_ctl_row else None
    if today_ctl is not None and prev_ctl is not None:
        ctl_delta = round(float(today_ctl) - float(prev_ctl), 1)

    tsb_row = conn.execute(
        "SELECT numeric_value FROM metric_store"
        " WHERE scope_type = 'daily' AND metric_name = 'tsb'"
        "   AND is_primary = 1 AND scope_id = ?",
        (act_date,),
    ).fetchone()
    tsb: float | None = None
    if tsb_row and tsb_row["numeric_value"] is not None:
        tsb = round(float(tsb_row["numeric_value"]), 1)

    return ctl_delta, tsb


def _similar_activities(
    conn: sqlite3.Connection,
    act_start_time: str,
    act_type: str,
    distance_m: float,
    act_pace: float | None,
) -> dict | None:
    """이전 유사 활동 비교. 3건 미만이면 None."""
    if act_pace is None:
        return None

    lo = distance_m * 0.85
    hi = distance_m * 1.15

    rows = conn.execute(
        "SELECT avg_pace_sec_km FROM v_canonical_activities"
        " WHERE activity_type = ? AND distance_m >= ? AND distance_m <= ?"
        "   AND start_time < ? AND avg_pace_sec_km IS NOT NULL"
        " ORDER BY start_time DESC LIMIT 10",
        (act_type, lo, hi, act_start_time),
    ).fetchall()

    if len(rows) < 3:
        return None

    paces = [float(r["avg_pace_sec_km"]) for r in rows]
    n = len(paces)
    avg_pace = round(sum(paces) / n, 1)
    faster = sum(1 for p in paces if p < act_pace)
    pace_rank = faster + 1
    pace_diff = round(float(act_pace) - avg_pace, 1)

    return {
        "n": n,
        "pace_rank": pace_rank,
        "avg_pace_sec_km": avg_pace,
        "pace_diff_sec": pace_diff,
    }


def _nearest_race(conn: sqlite3.Connection, today: str) -> dict | None:
    """오늘 이후 가장 가까운 활성 목표. 없으면 None."""
    row = conn.execute(
        "SELECT name, race_date FROM goals"
        " WHERE status = 'active' AND race_date IS NOT NULL AND race_date >= ?"
        " ORDER BY race_date ASC, id DESC LIMIT 1",
        (today,),
    ).fetchone()

    if row is None:
        return None

    days_left = (_date.fromisoformat(row["race_date"]) - _date.fromisoformat(today)).days
    return {"name": row["name"], "days_left": days_left}
