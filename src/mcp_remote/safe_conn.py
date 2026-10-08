"""읽기 전용 SQLite 연결 — mode=ro + query_only + authorizer(ATTACH 포함 쓰기 거부) + 쿼리 시간 제한."""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path

_ALLOWED_ACTIONS = {
    sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION,
    sqlite3.SQLITE_RECURSIVE,
}
_ARG_PRAGMAS = {  # PRAGMA name(arg) — 인자는 테이블/인덱스 이름
    "table_info", "table_xinfo", "index_list", "index_info", "index_xinfo", "foreign_key_list",
}
_BARE_PRAGMAS = {  # 값 대입(arg2 있음)은 쓰기이므로 거부
    "table_list", "user_version", "data_version", "schema_version", "page_count",
    "page_size", "freelist_count", "encoding", "collation_list",
}
DEFAULT_TIME_LIMIT_S = 5.0


def _authorizer(action, arg1, arg2, dbname, source):
    if action in _ALLOWED_ACTIONS:
        return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_PRAGMA and (arg1 in _ARG_PRAGMAS or (arg1 in _BARE_PRAGMAS and arg2 is None)):
        return sqlite3.SQLITE_OK
    return sqlite3.SQLITE_DENY


def connect_readonly(db_path: Path, time_limit_s: float = DEFAULT_TIME_LIMIT_S) -> sqlite3.Connection:
    """쓰기·ATTACH 불가, time_limit_s 초과 쿼리는 중단되는 연결."""
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.execute("PRAGMA query_only=ON")
    deadline = time.monotonic() + time_limit_s

    def _progress() -> int:
        return 1 if time.monotonic() > deadline else 0

    conn.set_progress_handler(_progress, 10000)
    conn.set_authorizer(_authorizer)
    return conn
