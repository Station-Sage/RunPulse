"""스키마 v47 — insight_events: 능동 인사이트 사건 저장소(V2-REPAIR D).

조정 신호의 상태 변화를 사건으로 기록한다(kind·severity·dedupe_key·state). 열린 사건은 dedupe_key 당 1개.
가산 테이블, 멱등.
"""
from __future__ import annotations

import sqlite3


def ensure_v47(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS insight_events (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            kind         TEXT NOT NULL,
            severity     TEXT NOT NULL CHECK (severity IN ('info','watch','act')),
            as_of        TEXT NOT NULL,
            dedupe_key   TEXT NOT NULL,
            signals_json TEXT,
            text         TEXT NOT NULL,
            action_json  TEXT,
            state        TEXT NOT NULL DEFAULT 'open' CHECK (state IN ('open','seen','dismissed','resolved')),
            created_at   TEXT NOT NULL DEFAULT (datetime('now')),
            resolved_at  TEXT,
            dismissed_at TEXT,
            text_ai      TEXT,
            text_src     TEXT
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_insight_events_key_state ON insight_events(dedupe_key, state)"
    )
    cols = {r[1] for r in conn.execute("PRAGMA table_info(insight_events)").fetchall()}
    for c in ("text_ai", "text_src"):
        if c not in cols:
            conn.execute(f"ALTER TABLE insight_events ADD COLUMN {c} TEXT")
