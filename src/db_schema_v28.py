"""스키마 v28 — goals.reported_weekly_km·reported_long_km (목표 생성 시 사용자가 입력한 최근 주간 km·최장 롱런 km)."""
from __future__ import annotations

import sqlite3

_COLS = ("reported_weekly_km", "reported_long_km")


def ensure_v28(conn: sqlite3.Connection) -> None:
    """goals 에 사용자 입력 시작 부하 컬럼 보장(기존 행 = NULL). 멱등."""
    cols = {r[1] for r in conn.execute("PRAGMA table_info(goals)").fetchall()}
    for col in _COLS:
        if cols and col not in cols:
            conn.execute(f"ALTER TABLE goals ADD COLUMN {col} REAL")
