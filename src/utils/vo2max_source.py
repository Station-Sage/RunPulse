"""Garmin VO2max 값 선택 — 일별 정밀값(maxmet)과 활동별 정수값 중 더 최근 측정 우선 (DESIGN-GARMIN-VO2MAX-PRECISE D3).

동일 날짜면 정밀값 우선. 반환 source: "precise" | "activity" | None.
"""
from __future__ import annotations

import sqlite3

_PRECISE = (
    "SELECT scope_id, numeric_value FROM metric_store WHERE scope_type='daily'"
    " AND provider='garmin' AND metric_name='vo2max' AND numeric_value IS NOT NULL"
)
_ACTIVITY = (
    "SELECT substr(a.start_time,1,10), m.numeric_value FROM metric_store m"
    " JOIN activity_summaries a ON CAST(a.id AS TEXT)=m.scope_id"
    " WHERE m.scope_type='activity' AND m.provider='garmin' AND m.metric_name='vo2max_activity'"
    " AND m.numeric_value IS NOT NULL"
)


def _latest(conn: sqlite3.Connection, sql: str, lo: str | None, hi: str | None):
    where, args = "", []
    if lo:
        where += " AND {col} >= ?"
        args.append(lo)
    if hi:
        where += " AND {col} <= ?"
        args.append(hi)
    col = "scope_id" if sql is _PRECISE else "substr(a.start_time,1,10)"
    try:
        return conn.execute(
            sql + where.format(col=col) + f" ORDER BY {col} DESC LIMIT 1", args
        ).fetchone()
    except sqlite3.OperationalError:
        return None


def garmin_vo2max_between(conn: sqlite3.Connection, lo: str | None = None,
                          hi: str | None = None) -> tuple[float | None, str | None]:
    """[lo, hi] (YYYY-MM-DD, 양끝 포함) 구간의 가장 최근 Garmin VO2max."""
    p = _latest(conn, _PRECISE, lo, hi)
    a = _latest(conn, _ACTIVITY, lo, hi)
    if p and (not a or p[0] >= a[0]):
        return float(p[1]), "precise"
    if a:
        return float(a[1]), "activity"
    return None, None


def garmin_vo2max_asof(conn: sqlite3.Connection, as_of: str | None = None
                       ) -> tuple[float | None, str | None]:
    """as_of 이하 가장 최근 값 (None 이면 전체 최신)."""
    return garmin_vo2max_between(conn, None, as_of)
