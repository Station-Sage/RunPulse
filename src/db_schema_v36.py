"""스키마 v36 — 퇴역 테이블 정리: running.db 의 구 sync_jobs(원장은 sync_jobs.db)와 ui_events 삭제."""
from __future__ import annotations

import sqlite3


def ensure_v36(conn: sqlite3.Connection) -> None:
    """구 sync_jobs·ui_events 테이블을 지운다. 없으면 건너뜀(멱등)."""
    conn.execute("DROP TABLE IF EXISTS sync_jobs")
    conn.execute("DROP TABLE IF EXISTS ui_events")
