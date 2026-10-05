"""v25 스키마(activity_feedback·user_settings) 테스트."""
import sqlite3

import pytest

from src.db_schema_v25 import ensure_v25
from src.db_setup import SCHEMA_VERSION, create_tables, get_db_path  # noqa: F401


def _conn():
    c = sqlite3.connect(":memory:")
    ensure_v25(c)
    return c


def test_tables_created_and_idempotent():
    c = _conn()
    ensure_v25(c)
    names = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"activity_feedback", "user_settings"} <= names


@pytest.mark.parametrize("rpe", [0, 11])
def test_rpe_check_rejects_out_of_range(rpe):
    c = _conn()
    with pytest.raises(sqlite3.IntegrityError):
        c.execute("INSERT INTO activity_feedback(activity_id, rpe) VALUES (1, ?)", (rpe,))


def test_note_length_check():
    c = _conn()
    c.execute("INSERT INTO activity_feedback(activity_id, note) VALUES (1, ?)", ("a" * 500,))
    with pytest.raises(sqlite3.IntegrityError):
        c.execute("INSERT INTO activity_feedback(activity_id, note) VALUES (2, ?)", ("a" * 501,))


def test_create_tables_wires_v25_and_version():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    assert c.execute("SELECT count(*) FROM activity_feedback").fetchone()[0] == 0
    assert SCHEMA_VERSION >= 25
