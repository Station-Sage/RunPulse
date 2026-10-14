"""'오늘' 기준일 헬퍼 — 최근 활동의 UTC 오프셋으로 사용자 현지 날짜를 구한다 (TZ T5, TZ-17/18/21).

서버 시계는 UTC 일 수 있어 `date('now','localtime')` 이 사용자의 오늘과 어긋난다.
최근 활동(시간대 추정 포함, 기간 제한 없음)에서 오프셋을 구하고, 못 구하면 더 이전 활동으로
거슬러 올라가며, 끝내 없으면 서버 로컬로 폴백한다.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone

from src.utils.tz_peers import _offset_of, _dt, _read_garmin, _read_intervals

_MAX_LOOKBACK = 30


def _payload_offset(conn: sqlite3.Connection, activity_id: int, start_time: str | None) -> int | None:
    rows = conn.execute(
        "SELECT source, entity_type, payload FROM source_payloads WHERE activity_id = ?",
        (activity_id,),
    ).fetchall()
    for source, etype, payload in rows:
        try:
            p = json.loads(payload)
        except (ValueError, TypeError):
            continue
        pt = None
        if source == "garmin" and etype == "activity_summary":
            pt = _read_garmin("", p)
        elif source == "intervals" and etype == "activity_summary":
            pt = _read_intervals("", p)
        if pt is not None and pt.utc and pt.local:
            off = _offset_of(pt.utc, pt.local)
            if off is not None:
                return off
        if source == "strava" and etype == "csv_export" and start_time:
            utc, local = _dt(p.get("start_date_utc")), _dt(start_time)
            if utc and local:
                off = _offset_of(utc, local)
                if off is not None:
                    return off
    return None


def reference_offset(conn: sqlite3.Connection) -> int | None:
    """최근 활동부터 거슬러 올라가 첫 유효 UTC 오프셋(초). 없으면 None."""
    rows = conn.execute(
        "SELECT id, start_time FROM activity_summaries ORDER BY start_time DESC LIMIT ?",
        (_MAX_LOOKBACK,),
    ).fetchall()
    for aid, st in rows:
        off = _payload_offset(conn, aid, st)
        if off is not None:
            return off
    return None


def reference_today(
    conn: sqlite3.Connection, now_utc: datetime | None = None,
) -> tuple[str, str]:
    """(오늘 'YYYY-MM-DD', basis). basis = 'activity_tz' | 'server_local'."""
    off = reference_offset(conn)
    if off is not None:
        now = now_utc or datetime.now(timezone.utc)
        now = now.replace(tzinfo=None) if now.tzinfo is None else now.astimezone(timezone.utc).replace(tzinfo=None)
        return (now + timedelta(seconds=off)).strftime("%Y-%m-%d"), "activity_tz"
    return conn.execute("SELECT date('now','localtime')").fetchone()[0], "server_local"
