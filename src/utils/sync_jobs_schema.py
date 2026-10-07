"""sync_jobs.db 스키마 — 테이블 생성과 원장 열(error_code·http_status·source_path·counts_json·trigger·started_at·finished_at) 멱등 보장."""
from __future__ import annotations

import sqlite3

CREATE_SQL = """CREATE TABLE IF NOT EXISTS sync_jobs (
    id TEXT PRIMARY KEY,
    service TEXT NOT NULL,
    from_date TEXT NOT NULL,
    to_date TEXT NOT NULL,
    window_days INTEGER NOT NULL DEFAULT 14,
    current_from TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    completed_days INTEGER NOT NULL DEFAULT 0,
    total_days INTEGER NOT NULL DEFAULT 0,
    synced_count INTEGER NOT NULL DEFAULT 0,
    req_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    retry_after TEXT,
    last_error TEXT
)"""

LEDGER_COLUMNS = {
    "error_code": "TEXT", "http_status": "INTEGER", "source_path": "TEXT",
    "counts_json": "TEXT", "trigger": "TEXT", "started_at": "TEXT", "finished_at": "TEXT",
}

_ensured: set[str] = set()


def ensure_ledger(conn: sqlite3.Connection, path: str) -> None:
    """테이블·인덱스·원장 열을 보장한다. 경로별로 PRAGMA 검사는 프로세스당 1회."""
    conn.execute(CREATE_SQL)
    if path in _ensured:
        return
    cols = {r[1] for r in conn.execute("PRAGMA table_info(sync_jobs)")}
    for name, decl in LEDGER_COLUMNS.items():
        if name not in cols:
            conn.execute(f"ALTER TABLE sync_jobs ADD COLUMN {name} {decl}")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_sync_jobs_service ON sync_jobs(service, created_at)"
    )
    _ensured.add(path)
