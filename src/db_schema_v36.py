"""스키마 v36 — ui_events (v2 방문·v1 복귀 클릭 기록, G5 게이트 판정용)."""
from __future__ import annotations

import sqlite3


def ensure_v36(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS ui_events (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          kind TEXT NOT NULL CHECK (kind IN ('v2_visit','v1_rollback')),
          reason TEXT CHECK (reason IS NULL OR reason IN
            ('missing_feature','hard_to_use','slow_or_error','just_looking')),
          reason_note TEXT CHECK (reason_note IS NULL OR length(reason_note) <= 200),
          day TEXT NOT NULL,
          created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE UNIQUE INDEX IF NOT EXISTS uq_ui_events_visit_day
          ON ui_events(day) WHERE kind='v2_visit';
        CREATE INDEX IF NOT EXISTS idx_ui_events_kind_day ON ui_events(kind, day);
        """
    )
