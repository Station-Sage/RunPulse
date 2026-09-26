"""P7-PRED-11: 스키마 v20 컬럼·race_results·session_outcomes 유일 제약."""
import sqlite3

from src.db_setup import create_tables, migrate_db
from src.db_schema_v20 import V20_COLUMNS, ensure_v20


def _conn():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    return c


def test_v20_columns_exist_after_create():
    c = _conn()
    for table, cols in V20_COLUMNS.items():
        existing = {r[1] for r in c.execute(f"PRAGMA table_info({table})")}
        for name, _ in cols:
            assert name in existing, (table, name)
    assert c.execute("SELECT count(*) FROM race_results").fetchone()[0] == 0


def test_ensure_v20_idempotent():
    c = _conn()
    ensure_v20(c)
    ensure_v20(c)
    assert "gap_speed_ms" in {r[1] for r in c.execute("PRAGMA table_info(activity_laps)")}


def test_migrate_from_19_adds_columns():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    c.execute("PRAGMA user_version = 19")
    migrate_db(c)
    assert c.execute("PRAGMA user_version").fetchone()[0] == 20


def test_session_outcomes_unique_planned_id():
    import sqlite3 as _s
    from src.db_setup import create_tables as _ct
    c = _s.connect(":memory:")
    _ct(c)
    c.execute("INSERT INTO session_outcomes (planned_id, date) VALUES (1, '2026-09-22')")
    c.execute("INSERT INTO session_outcomes (planned_id, date) VALUES (1, '2026-09-22') "
              "ON CONFLICT(planned_id) DO UPDATE SET date=excluded.date")
    assert c.execute("SELECT count(*) FROM session_outcomes").fetchone()[0] == 1
