"""스키마 v34 — caldav_pushes (CalDAV 로 보낸 일정의 날짜·슬롯·UID 기록, ADR-036)."""
from __future__ import annotations

import sqlite3


def ensure_v34(conn: sqlite3.Connection) -> None:
    """caldav_pushes 테이블을 만든다. 멱등."""
    conn.execute(
        "CREATE TABLE IF NOT EXISTS caldav_pushes ("
        " date TEXT NOT NULL, slot INTEGER NOT NULL, uid TEXT NOT NULL,"
        " pushed_at TEXT NOT NULL DEFAULT (datetime('now')), PRIMARY KEY (date, slot))")
