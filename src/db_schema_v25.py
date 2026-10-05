"""스키마 v25 — 활동 피드백(activity_feedback, ADR-022)·사용자 UI 설정(user_settings, ADR-023)."""
from __future__ import annotations

import sqlite3

_DDL = (
    """CREATE TABLE IF NOT EXISTS activity_feedback (
        activity_id  INTEGER PRIMARY KEY,
        rpe          INTEGER CHECK (rpe IS NULL OR rpe BETWEEN 1 AND 10),
        pain         TEXT,
        pain_sites   TEXT,
        note         TEXT CHECK (note IS NULL OR length(note) <= 500),
        created_at   TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at   TEXT NOT NULL DEFAULT (datetime('now'))
    )""",
    "CREATE INDEX IF NOT EXISTS idx_actfb_updated ON activity_feedback(updated_at)",
    """CREATE TABLE IF NOT EXISTS user_settings (
        key         TEXT PRIMARY KEY,
        value_json  TEXT NOT NULL,
        updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
    )""",
)


def ensure_v25(conn: sqlite3.Connection) -> None:
    """activity_feedback·user_settings 테이블 보장. 멱등."""
    for stmt in _DDL:
        conn.execute(stmt)
