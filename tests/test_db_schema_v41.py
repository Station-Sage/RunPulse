"""스키마 v41 (goals.plan_snapshot_json) 테스트."""
import sqlite3

from src.db_schema_v41 import ensure_v41
from src.db_setup import SCHEMA_VERSION, create_tables


def _cols(c):
    return {r[1] for r in c.execute("PRAGMA table_info(goals)")}


def test_adds_column_and_idempotent():
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE goals (id INTEGER PRIMARY KEY)")
    ensure_v41(c)
    ensure_v41(c)
    assert "plan_snapshot_json" in _cols(c)


def test_create_tables_reaches_v41():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    assert SCHEMA_VERSION >= 41
    assert "plan_snapshot_json" in _cols(c)
