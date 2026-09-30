"""스키마 v24 — chat_messages.client_msg_id·chat_threads 컬럼 (30-coach-chat design §6.2)."""
import sqlite3

import pytest

from src.db_schema_v24 import ensure_v24
from src.db_setup import SCHEMA_VERSION, create_tables, migrate_db


def _cols(c, table):
    return {r[1] for r in c.execute(f"PRAGMA table_info({table})")}


def test_create_tables_has_v24_columns():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    assert {"client_msg_id", "parent_message_id", "followups_json"} <= _cols(c, "chat_messages")
    assert {"context_kind", "context_ref", "title_source", "pinned", "deleted_at"} <= _cols(c, "chat_threads")


def test_ensure_v24_idempotent():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    ensure_v24(c)
    ensure_v24(c)
    assert "client_msg_id" in _cols(c, "chat_messages")


def test_migrate_from_23():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    c.execute("PRAGMA user_version = 23")
    migrate_db(c)
    assert c.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION >= 24


def test_client_msg_id_unique_per_thread():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    ins = "INSERT INTO chat_messages (role, content, thread_id, client_msg_id) VALUES ('user', 'x', ?, ?)"
    c.execute(ins, (1, "a"))
    c.execute(ins, (2, "a"))
    c.execute(ins, (1, None))
    c.execute(ins, (1, None))
    with pytest.raises(sqlite3.IntegrityError):
        c.execute(ins, (1, "a"))
