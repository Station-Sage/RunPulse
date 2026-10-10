import sqlite3

from src.db_schema_v36 import ensure_v36


def test_drops_retired_tables_idempotent():
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE sync_jobs(id TEXT)")
    c.execute("CREATE TABLE ui_events(id TEXT)")
    ensure_v36(c)
    ensure_v36(c)
    names = {r[0] for r in c.execute("SELECT name FROM sqlite_master")}
    assert not names & {"sync_jobs", "ui_events"}


def test_migrate_drops_legacy_in_old_db():
    from src.db_setup import create_tables, migrate_db
    c = sqlite3.connect(":memory:")
    create_tables(c)
    c.execute("CREATE TABLE sync_jobs(id TEXT)")
    c.execute("PRAGMA user_version=35")
    migrate_db(c)
    assert c.execute("SELECT 1 FROM sqlite_master WHERE name='sync_jobs'").fetchone() is None
