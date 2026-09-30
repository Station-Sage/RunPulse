"""스키마 v24 — Coach 비동기 답변 상태 기계(30-coach-chat design §6.2·§7.1).

chat_messages.client_msg_id(재전송 멱등, thread 내 UNIQUE) / parent_message_id(재생성 계보) / followups_json.
chat_threads.context_kind / context_ref / title_source / pinned / deleted_at.
"""
from __future__ import annotations

import sqlite3

_MESSAGE_COLUMNS = {
    "client_msg_id": "TEXT",
    "parent_message_id": "INTEGER",
    "followups_json": "TEXT",
}

_THREAD_COLUMNS = {
    "context_kind": "TEXT",
    "context_ref": "TEXT",
    "title_source": "TEXT DEFAULT 'auto'",
    "pinned": "INTEGER NOT NULL DEFAULT 0",
    "deleted_at": "TEXT",
}


def _cols(conn: sqlite3.Connection, table: str) -> set[str]:
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _add_missing(conn: sqlite3.Connection, table: str, columns: dict[str, str]) -> bool:
    cols = _cols(conn, table)
    if not cols:
        return False
    for name, decl in columns.items():
        if name not in cols:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {decl}")
    return True


def ensure_v24(conn: sqlite3.Connection) -> None:
    """Coach 메시지·스레드 컬럼과 client_msg_id 유일 인덱스 보장. 멱등."""
    if _add_missing(conn, "chat_messages", _MESSAGE_COLUMNS) and "thread_id" in _cols(conn, "chat_messages"):
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_chat_client_msg "
                     "ON chat_messages(thread_id, client_msg_id) WHERE client_msg_id IS NOT NULL")
    _add_missing(conn, "chat_threads", _THREAD_COLUMNS)
