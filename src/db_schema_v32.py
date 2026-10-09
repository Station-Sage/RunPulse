"""스키마 v32 — plan_replans(안전한 재계획 anchor, ADR-035 부록 R) + 활성 목표 1개 보장 유니크 인덱스."""
from __future__ import annotations

import sqlite3

_DDL = """
CREATE TABLE IF NOT EXISTS plan_replans (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    goal_id         INTEGER NOT NULL,
    anchor_monday   TEXT    NOT NULL,        -- 이 날짜(월요일) 이후 주만 재생성
    start_km        REAL    NOT NULL,        -- 시작 주간 거리
    start_long_km   REAL,                    -- 시작 롱런 거리
    start_source    TEXT    NOT NULL CHECK (start_source IN ('user','history')),
    target_time_sec INTEGER,
    replaced_json   TEXT    NOT NULL DEFAULT '{}',  -- 되돌리기용 삭제 행 스냅샷
    status          TEXT    NOT NULL DEFAULT 'applied' CHECK (status IN ('applied','undone')),
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    undone_at       TEXT
);
CREATE INDEX IF NOT EXISTS idx_plan_replans_goal ON plan_replans(goal_id, status, anchor_monday);
"""


def ensure_v32(conn: sqlite3.Connection) -> None:
    """plan_replans 와 ux_goals_one_active 보장. 중복 active 는 최신 1개만 남기고 cancelled. 멱등."""
    conn.executescript(_DDL)
    conn.execute(
        "UPDATE goals SET status='cancelled' WHERE status='active' AND id NOT IN ("
        " SELECT id FROM goals WHERE status='active' ORDER BY created_at DESC, id DESC LIMIT 1)"
    )
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_goals_one_active ON goals(status) WHERE status='active'")
