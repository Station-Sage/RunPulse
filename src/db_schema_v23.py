"""스키마 v23 — Coach 엔진 투명성(30-coach-chat design §4.3·§6.2).

chat_messages.status / engine_json / as_of / sent_scope_json — 답변을 만든 엔진·전송 범위 기록(규칙 답변의 sent_scope는 NULL).
coach_consent — LLM 전송 동의(계정당 1행): provider·범위 토글(메모 제외/도구 조회/대체 provider).
"""
from __future__ import annotations

import sqlite3

_MESSAGE_COLUMNS = {
    "status": "TEXT DEFAULT 'done'",
    "engine_json": "TEXT",
    "as_of": "TEXT",
    "sent_scope_json": "TEXT",
}

_DDL_CONSENT = """
CREATE TABLE IF NOT EXISTS coach_consent (
    id INTEGER PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    provider TEXT NOT NULL,
    accepted_at TEXT NOT NULL DEFAULT (datetime('now')),
    exclude_notes INTEGER NOT NULL DEFAULT 0,
    tools_enabled INTEGER NOT NULL DEFAULT 1,
    fallback_enabled INTEGER NOT NULL DEFAULT 1
)
"""


def ensure_v23(conn: sqlite3.Connection) -> None:
    """chat_messages 엔진 컬럼 + coach_consent 테이블 보장. 멱등."""
    conn.execute(_DDL_CONSENT)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(chat_messages)").fetchall()}
    if not cols:
        return
    for name, decl in _MESSAGE_COLUMNS.items():
        if name not in cols:
            conn.execute(f"ALTER TABLE chat_messages ADD COLUMN {name} {decl}")
