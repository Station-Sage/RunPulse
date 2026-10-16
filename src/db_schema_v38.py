"""스키마 v38 — 가산 CREATE: race_calendar·context_episodes·illness_consent_events (롤백 = DROP, v39 적용 전까지만)."""
from __future__ import annotations

import sqlite3

TABLES = ("race_calendar", "context_episodes", "illness_consent_events")

_ADAPT = "('unasked','later','adapt','no_adapt')"
_PLAN_STATE = "('none','applied','stale')"

_DDL = (
    f"""
CREATE TABLE IF NOT EXISTS race_calendar (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    name TEXT NOT NULL,
    race_date TEXT NOT NULL,
    distance_km REAL NOT NULL,
    priority TEXT NOT NULL CHECK (priority IN ('A','B','C')),
    goal_type TEXT CHECK (goal_type IN ('finish','time','pb') OR goal_type IS NULL),
    goal_value REAL,
    adapt_choice TEXT NOT NULL DEFAULT 'unasked' CHECK (adapt_choice IN {_ADAPT}),
    plan_state TEXT NOT NULL DEFAULT 'none' CHECK (plan_state IN {_PLAN_STATE}),
    cancel_prev_adapt_choice TEXT CHECK (cancel_prev_adapt_choice IN {_ADAPT} OR cancel_prev_adapt_choice IS NULL),
    cancel_prev_plan_state TEXT CHECK (cancel_prev_plan_state IN {_PLAN_STATE} OR cancel_prev_plan_state IS NULL),
    taper_days INTEGER,
    recovery_days INTEGER,
    status TEXT NOT NULL DEFAULT 'planned' CHECK (status IN ('planned','done','cancelled')),
    origin TEXT NOT NULL DEFAULT 'manual' CHECK (origin IN ('manual','goal','import')),
    planned_workout_id INTEGER REFERENCES planned_workouts(id),
    race_result_id INTEGER REFERENCES race_results(id),
    note TEXT
)""",
    "CREATE UNIQUE INDEX IF NOT EXISTS ux_race_planned_same ON race_calendar(race_date, distance_km)"
    " WHERE status = 'planned'",
    "CREATE UNIQUE INDEX IF NOT EXISTS ux_race_one_a ON race_calendar(priority)"
    " WHERE priority = 'A' AND status = 'planned'",
    """
CREATE TABLE IF NOT EXISTS context_episodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL CHECK (kind IN ('illness','travel','altitude')),
    start_date TEXT NOT NULL,
    end_date TEXT,
    severity INTEGER,
    detail_json TEXT NOT NULL DEFAULT '{}',
    origin TEXT NOT NULL CHECK (origin IN ('user','auto')),
    status TEXT NOT NULL CHECK (status IN ('candidate','confirmed','dismissed')),
    last_confirmed_date TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
)""",
    """
CREATE TABLE IF NOT EXISTS illness_consent_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT NOT NULL CHECK (action IN ('grant','decline','revoke')),
    via TEXT NOT NULL CHECK (via IN ('first_input','settings')),
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
)""",
)


def dry_run(conn: sqlite3.Connection) -> list[str]:
    """생성될 테이블 중 아직 없는 것(쓰기 없음)."""
    have = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    return [t for t in TABLES if t not in have]


def ensure_v38(conn: sqlite3.Connection) -> None:
    """3개 테이블·인덱스를 만든다(IF NOT EXISTS, 멱등). 기존 데이터는 건드리지 않는다."""
    for ddl in _DDL:
        conn.execute(ddl)
