"""스키마 v26 — goals.plan_rules_version (U16 계획 규칙 버전을 목표별로 고정)."""
from __future__ import annotations

import sqlite3


def ensure_v26(conn: sqlite3.Connection) -> None:
    """goals.plan_rules_version 컬럼 보장(기존 행 = 1). 멱등."""
    cols = {r[1] for r in conn.execute("PRAGMA table_info(goals)").fetchall()}
    if cols and "plan_rules_version" not in cols:
        conn.execute(
            "ALTER TABLE goals ADD COLUMN plan_rules_version INTEGER NOT NULL DEFAULT 1"
        )
