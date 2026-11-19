"""스키마 v50 — context_episodes.kind CHECK 에 'injury'(부상) 추가 (ADR-057).

SQLite 는 CHECK 를 바꿀 수 없어 테이블을 재생성한다(컬럼·행·id·인덱스 보존, v27 방식). 이 테이블을 참조하는 FK 는 없다.
create_tables 가 매 요청 부르므로 CHECK 에 'injury' 가 이미 있으면 아무것도 하지 않는다(멱등).
"""
from __future__ import annotations

import sqlite3

_OLD = "'illness','travel','altitude')"
_NEW = "'illness','travel','altitude','injury')"


def needs_rebuild(conn: sqlite3.Connection) -> bool:
    row = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='context_episodes'").fetchone()
    return bool(row and row[0] and "'injury'" not in row[0] and _OLD in row[0])


def ensure_v50(conn: sqlite3.Connection) -> None:
    """kind CHECK 확장. 기존 데이터·인덱스를 그대로 옮긴다."""
    if not needs_rebuild(conn):
        return
    sql = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='context_episodes'").fetchone()[0]
    new_sql = sql.replace(_OLD, _NEW, 1).replace("context_episodes", "context_episodes__v50", 1)
    indexes = [r[0] for r in conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='index' AND tbl_name='context_episodes' AND sql IS NOT NULL")]
    cols = ", ".join(f'"{r[1]}"' for r in conn.execute("PRAGMA table_info(context_episodes)"))
    conn.execute("DROP TABLE IF EXISTS context_episodes__v50")
    conn.execute(new_sql)
    conn.execute(f"INSERT INTO context_episodes__v50 ({cols}) SELECT {cols} FROM context_episodes")
    conn.execute("DROP TABLE context_episodes")
    conn.execute("ALTER TABLE context_episodes__v50 RENAME TO context_episodes")
    for idx in indexes:
        conn.execute(idx)
    conn.commit()
