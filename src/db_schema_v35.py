"""스키마 v35 — plan_replans.rules_version (anchor 별 계획 규칙 버전, NULL=목표 값을 따름)."""
from __future__ import annotations

import sqlite3


def ensure_v35(conn: sqlite3.Connection) -> None:
    """plan_replans 에 rules_version 컬럼을 추가한다. 테이블이 없거나 이미 있으면 건너뜀(멱등)."""
    cols = [r[1] for r in conn.execute("PRAGMA table_info(plan_replans)").fetchall()]
    if cols and "rules_version" not in cols:
        conn.execute("ALTER TABLE plan_replans ADD COLUMN rules_version INTEGER CHECK (rules_version IN (1,2))")
