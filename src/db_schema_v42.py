"""스키마 v42 — 신발 관리 v2(V2-SHOES): user_shoes·activity_shoe 신설 + gear.shoe_id.

가산 변경만(백필 없음), 멱등. `gear` 는 소스 미러, `user_shoes` 는 사용자 소유(동기화가 건드리지 않음).
`activity_shoe.activity_id` 는 activity_feedback 과 같은 관례로 FK 를 두지 않는다(재처리 시 activity_summaries
삭제가 CASCADE 로 사용자 배정을 지우지 않게). origin='rule' 행은 기본 신발 교체·은퇴 시 고정한 기본 규칙 이력.
기존 v1 `shoes` 테이블은 건드리지 않는다(Q9).
"""
from __future__ import annotations

import logging
import sqlite3

log = logging.getLogger(__name__)

TABLES = ("user_shoes", "activity_shoe")

_DDL = (
    """
CREATE TABLE IF NOT EXISTS user_shoes (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    name                TEXT NOT NULL,
    brand               TEXT,
    model               TEXT,
    category            TEXT NOT NULL DEFAULT 'daily'
                        CHECK (category IN ('daily','tempo','race','trail','other')),
    start_date          TEXT,
    initial_distance_m  REAL NOT NULL DEFAULT 0 CHECK (initial_distance_m >= 0),
    retire_km           INTEGER CHECK (retire_km BETWEEN 100 AND 2000),
    default_for         TEXT CHECK (default_for IN ('road','trail','treadmill')),
    default_since       TEXT,
    retired_at          TEXT,
    origin              TEXT NOT NULL DEFAULT 'manual' CHECK (origin IN ('manual','gear')),
    notes               TEXT,
    created_at          TEXT DEFAULT (datetime('now')),
    updated_at          TEXT DEFAULT (datetime('now'))
)""",
    "CREATE UNIQUE INDEX IF NOT EXISTS ux_user_shoes_default ON user_shoes(default_for)"
    " WHERE default_for IS NOT NULL AND retired_at IS NULL",
    """
CREATE TABLE IF NOT EXISTS activity_shoe (
    activity_id  INTEGER PRIMARY KEY,
    shoe_id      INTEGER REFERENCES user_shoes(id) ON DELETE CASCADE,
    origin       TEXT NOT NULL DEFAULT 'manual' CHECK (origin IN ('manual','rule')),
    created_at   TEXT DEFAULT (datetime('now'))
)""",
    "CREATE INDEX IF NOT EXISTS idx_activity_shoe_shoe ON activity_shoe(shoe_id)",
)


def _has_col(conn: sqlite3.Connection, table: str, col: str) -> bool:
    return any(r[1] == col for r in conn.execute(f"PRAGMA table_info({table})"))


def ensure_v42(conn: sqlite3.Connection) -> None:
    """테이블 2개·gear.shoe_id 를 없을 때만 만든다. 이미 있으면 integrity_check 도 생략(멱등)."""
    have = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    need_col = "gear" in have and not _has_col(conn, "gear", "shoe_id")
    if not need_col and all(t in have for t in TABLES):
        return
    check = conn.execute("PRAGMA integrity_check").fetchone()[0]
    if check != "ok":
        raise RuntimeError(f"v42 중단: integrity_check={check}")
    for ddl in _DDL:
        conn.execute(ddl)
    if need_col:
        conn.execute("ALTER TABLE gear ADD COLUMN shoe_id INTEGER REFERENCES user_shoes(id) ON DELETE SET NULL")
    if "gear" in have or need_col:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_gear_shoe ON gear(shoe_id)")
    log.info("v42: user_shoes·activity_shoe·gear.shoe_id 보장")
