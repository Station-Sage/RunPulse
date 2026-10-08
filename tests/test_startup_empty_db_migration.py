"""빈 사용자 DB(가입 직후)에 create_tables → migrate_db 순서로 적용하면 실패하지 않는다."""
import sqlite3

import pytest

from src.db_setup import create_tables, migrate_db


def test_migrate_alone_fails_on_empty_db(tmp_path):
    conn = sqlite3.connect(tmp_path / "empty.db")
    with pytest.raises(sqlite3.OperationalError):
        migrate_db(conn)
    conn.close()


def test_create_tables_then_migrate_on_empty_db(tmp_path):
    conn = sqlite3.connect(tmp_path / "empty.db")
    create_tables(conn)
    migrate_db(conn)
    assert conn.execute("SELECT COUNT(*) FROM activity_summaries").fetchone()[0] == 0
    conn.close()
