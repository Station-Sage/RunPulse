"""스키마 v51 — goals.plan_method·plan_replans.plan_method (훈련 방식 축, ADR-060).

goals.plan_method 은 NOT NULL DEFAULT 'balanced'(기존 행 = 현행 규칙), plan_replans.plan_method 는 nullable
(NULL = 방식 변경 없음). 가산, 멱등.
"""
from __future__ import annotations

import sqlite3


def _cols(conn: sqlite3.Connection, table: str) -> set[str]:
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def ensure_v51(conn: sqlite3.Connection) -> None:
    """두 컬럼을 보장한다(테이블이 없으면 건너뜀)."""
    cols = _cols(conn, "goals")
    if cols and "plan_method" not in cols:
        conn.execute("ALTER TABLE goals ADD COLUMN plan_method TEXT NOT NULL DEFAULT 'balanced'")
    cols = _cols(conn, "plan_replans")
    if cols and "plan_method" not in cols:
        conn.execute("ALTER TABLE plan_replans ADD COLUMN plan_method TEXT")
