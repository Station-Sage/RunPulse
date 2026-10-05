"""활동 상세 임팩트 — CTL Δ·유사 활동 비교·레이스 맥락.

읽기 전용. DB 쓰기 없음.
첫 번째 인자는 sqlite3.Connection.
반환값은 dict 또는 None (러닝 계열 활동만 지원).
"""
from __future__ import annotations

import sqlite3
from datetime import date as _date

from src.services.activity_similar import find_similar


def get_activity_impact(
    conn: sqlite3.Connection,
    activity_id: int,
    today: _date | None = None,
) -> dict | None:
    """활동이 훈련 부하·동류 활동·레이스 맥락에서 어디에 위치하는지 반환.

    러닝 계열(activity_type LIKE '%running%')이 아니거나 거리가 없으면 None.
    반환: {"load", "ctl_contribution", "tsb", "tsb_as_of", "similar", "race"}.
    load는 이 활동의 TRIMP, ctl_contribution은 활동일 CTL의 전일 대비 변화(그날 다른 활동 포함).
    """
    conn.row_factory = sqlite3.Row

    act = conn.execute(
        "SELECT id, activity_type, start_time, distance_m, avg_pace_sec_km, avg_hr, start_lat, start_lon"
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
    load = _activity_load(conn, activity_id)
    similar = find_similar(
        conn, activity_id, act_start_time, act["distance_m"], act["avg_pace_sec_km"],
        act["start_lat"], act["start_lon"],
    )
    race = _nearest_race(conn, act_date)

    return {
        "load": load,
        "ctl_contribution": ctl_delta,
        "tsb": tsb,
        "tsb_as_of": act_date if tsb is not None else None,
        "similar": similar,
        "race": race,
    }


def _activity_load(conn: sqlite3.Connection, activity_id: int) -> float | None:
    """활동 TRIMP(primary). 없으면 None."""
    row = conn.execute(
        "SELECT numeric_value FROM metric_store"
        " WHERE scope_type = 'activity' AND metric_name = 'trimp'"
        "   AND is_primary = 1 AND scope_id = CAST(? AS TEXT) LIMIT 1",
        (activity_id,),
    ).fetchone()
    if row is None or row["numeric_value"] is None:
        return None
    return round(float(row["numeric_value"]), 1)


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


_RACE_CONTEXT_DAYS = 120


def _nearest_race(conn: sqlite3.Connection, act_date: str) -> dict | None:
    """활동일 이후 가장 가까운 활성 목표 — 활동일 기준 D-day. 120일 넘게 남았으면 맥락으로 보지 않는다.

    (명세는 '오늘' 기준이라 과거 활동에도 현재 레이스 D-day가 붙는 결함이 있어 활동일 기준으로 교정.)
    """
    row = conn.execute(
        "SELECT name, race_date FROM goals"
        " WHERE status = 'active' AND race_date IS NOT NULL AND race_date >= ?"
        " ORDER BY race_date ASC, id DESC LIMIT 1",
        (act_date,),
    ).fetchone()

    if row is None:
        return None

    days_left = (_date.fromisoformat(row["race_date"]) - _date.fromisoformat(act_date)).days
    if days_left > _RACE_CONTEXT_DAYS:
        return None
    return {"name": row["name"], "days_left": days_left}
