"""스키마 v49 — milestones.source_ref 추가(멱등, 기존 행 보존)."""
import sqlite3

from src.db_schema_v49 import ensure_v49


def test_adds_source_ref_idempotent():
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE milestones (id INTEGER PRIMARY KEY, type TEXT NOT NULL, date TEXT NOT NULL,"
              " title TEXT NOT NULL, UNIQUE(type, date, title))")
    c.execute("INSERT INTO milestones(type, date, title) VALUES ('pb', '2026-01-01', '5K PB')")
    ensure_v49(c)
    ensure_v49(c)
    cols = {r[1] for r in c.execute("PRAGMA table_info(milestones)")}
    assert "source_ref" in cols
    assert c.execute("SELECT title, source_ref FROM milestones").fetchall() == [("5K PB", None)]


def test_no_table_is_noop():
    c = sqlite3.connect(":memory:")
    ensure_v49(c)
    assert c.execute("SELECT count(*) FROM sqlite_master").fetchone()[0] == 0
