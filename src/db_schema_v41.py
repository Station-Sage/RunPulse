"""스키마 v41 — goals.plan_snapshot_json (PLN-43: 교체·취소된 목표의 플랜 스냅샷 보관, 복원용).

nullable 컬럼 1개 추가, 백필 없음, 멱등.
"""
from __future__ import annotations

import logging
import sqlite3

log = logging.getLogger(__name__)


def ensure_v41(conn: sqlite3.Connection) -> None:
    """goals.plan_snapshot_json 이 없을 때만 추가."""
    if any(r[1] == "plan_snapshot_json" for r in conn.execute("PRAGMA table_info(goals)")):
        return
    check = conn.execute("PRAGMA integrity_check").fetchone()[0]
    if check != "ok":
        raise RuntimeError(f"v41 중단: integrity_check={check}")
    conn.execute("ALTER TABLE goals ADD COLUMN plan_snapshot_json TEXT")
    log.info("v41: goals.plan_snapshot_json 추가")
