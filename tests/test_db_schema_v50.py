"""스키마 v50 — context_episodes.kind CHECK 에 injury 추가(재생성, 행·id·인덱스 보존, 멱등)."""
import sqlite3

import pytest

from src.db_schema_v38 import ensure_v38
from src.db_schema_v50 import ensure_v50, needs_rebuild


def test_rebuild_preserves_rows_and_indexes():
    c = sqlite3.connect(":memory:")
    ensure_v38(c)
    c.execute("INSERT INTO context_episodes(id, kind, start_date, origin, status) VALUES (7,'illness','2026-01-01','user','confirmed')")
    with pytest.raises(sqlite3.IntegrityError):
        c.execute("INSERT INTO context_episodes(kind, start_date, origin, status) VALUES ('injury','2026-01-02','user','confirmed')")
    assert needs_rebuild(c)
    ensure_v50(c)
    ensure_v50(c)
    assert not needs_rebuild(c)
    assert c.execute("SELECT id, kind FROM context_episodes").fetchall() == [(7, "illness")]
    c.execute("INSERT INTO context_episodes(kind, start_date, origin, status) VALUES ('injury','2026-01-02','user','confirmed')")
    assert c.execute("SELECT max(id) FROM context_episodes").fetchone()[0] == 8
    idx = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='context_episodes'")}
    assert "idx_episodes_kind_status" in idx
    with pytest.raises(sqlite3.IntegrityError):
        c.execute("INSERT INTO context_episodes(kind, start_date, origin, status) VALUES ('flu','2026-01-02','user','confirmed')")


def test_fresh_db_has_injury(db_conn):
    sql = db_conn.execute("SELECT sql FROM sqlite_master WHERE name='context_episodes'").fetchone()[0]
    assert "'injury'" in sql
