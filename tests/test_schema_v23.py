"""스키마 v23 — chat_messages 엔진 컬럼·coach_consent (30-coach-chat design §4.3·§6.2)."""
import sqlite3

from src.db_schema_v23 import ensure_v23
from src.db_setup import SCHEMA_VERSION, create_tables, migrate_db


def _cols(c, table):
    return {r[1] for r in c.execute(f"PRAGMA table_info({table})")}


def test_create_tables_has_v23_columns_and_consent():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    assert {"status", "engine_json", "as_of", "sent_scope_json"} <= _cols(c, "chat_messages")
    assert {"provider", "exclude_notes", "tools_enabled", "fallback_enabled"} <= _cols(c, "coach_consent")


def test_ensure_v23_idempotent():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    ensure_v23(c)
    ensure_v23(c)
    assert "engine_json" in _cols(c, "chat_messages")


def test_migrate_from_22():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    c.execute("PRAGMA user_version = 22")
    migrate_db(c)
    assert c.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION >= 23


def test_consent_single_row_only():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    c.execute("INSERT INTO coach_consent (provider) VALUES ('gemini')")
    try:
        c.execute("INSERT INTO coach_consent (id, provider) VALUES (2, 'groq')")
        raise AssertionError("id=2 허용됨")
    except sqlite3.IntegrityError:
        pass
