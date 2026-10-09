"""스키마 v33 — plan_replans.start_source CHECK 확장 ('floor','avg16','default' 추가, ADR-035 부록 R Q7)."""
from __future__ import annotations

import sqlite3

_COLS = ("id, goal_id, anchor_monday, start_km, start_long_km, start_source, target_time_sec,"
         " replaced_json, status, created_at, undone_at")

_DDL = """
CREATE TABLE plan_replans_new (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    goal_id         INTEGER NOT NULL,
    anchor_monday   TEXT    NOT NULL,
    start_km        REAL    NOT NULL,
    start_long_km   REAL,
    start_source    TEXT    NOT NULL CHECK (start_source IN ('user','history','floor','avg16','default')),
    target_time_sec INTEGER,
    replaced_json   TEXT    NOT NULL DEFAULT '{}',
    status          TEXT    NOT NULL DEFAULT 'applied' CHECK (status IN ('applied','undone')),
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    undone_at       TEXT
);
"""


def ensure_v33(conn: sqlite3.Connection) -> None:
    """start_source CHECK 가 아직 옛 값만 허용하면 테이블을 복사 재생성한다. 행·인덱스 보존, 멱등."""
    row = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='plan_replans'").fetchone()
    if row is None or "'avg16'" in row[0]:
        return
    conn.execute("DROP TABLE IF EXISTS plan_replans_new")
    conn.executescript(_DDL)
    conn.execute(f"INSERT INTO plan_replans_new({_COLS}) SELECT {_COLS} FROM plan_replans")
    conn.execute("DROP TABLE plan_replans")
    conn.execute("ALTER TABLE plan_replans_new RENAME TO plan_replans")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_plan_replans_goal ON plan_replans(goal_id, status, anchor_monday)")
