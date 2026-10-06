"""스키마 v29 — plan_progression (목표별 품질 세션 사다리 단계, DESIGN-U16 §3.3)."""
from __future__ import annotations

import sqlite3


def ensure_v29(conn: sqlite3.Connection) -> None:
    """plan_progression 테이블 보장. 멱등."""
    conn.execute("""CREATE TABLE IF NOT EXISTS plan_progression (
        goal_id INTEGER NOT NULL, qtype TEXT NOT NULL, step INTEGER NOT NULL DEFAULT 0,
        updated_at TEXT NOT NULL DEFAULT (datetime('now')), reason TEXT,
        PRIMARY KEY (goal_id, qtype))""")
