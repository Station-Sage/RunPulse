"""스키마 v30 — activity_stream_meta (활동×소스 스트림 시간축 출처·통계, DESIGN-U18 §3)."""
from __future__ import annotations

import sqlite3


def ensure_v30(conn: sqlite3.Connection) -> None:
    """activity_stream_meta 테이블 보장. 멱등. activity_streams 는 건드리지 않는다."""
    conn.execute("""CREATE TABLE IF NOT EXISTS activity_stream_meta (
        activity_id   INTEGER NOT NULL,
        source        TEXT    NOT NULL,
        time_basis    TEXT    NOT NULL CHECK (time_basis IN ('measured','derived','scaled','unknown')),
        time_key      TEXT,
        sample_count  INTEGER NOT NULL,
        stored_count  INTEGER NOT NULL,
        span_sec      REAL,
        median_dt_sec REAL,
        extracted_at  TEXT DEFAULT (datetime('now')),
        PRIMARY KEY (activity_id, source))""")
