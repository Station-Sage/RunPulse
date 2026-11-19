"""스키마 v49 — milestones.source_ref(출처 연결 키) + 조회 인덱스 (ADR-057).

source_ref = '<출처>:<id>' (race_result:<activity_id>·goal:<id>·race:<id>·episode:<id>·replan:<id>).
출처가 삭제·취소되면 같은 키의 마일스톤도 지운다. 동기화 탐지(누적 거리·PB·최장거리·연속 주)는 NULL. 가산, 멱등.
"""
from __future__ import annotations

import sqlite3


def ensure_v49(conn: sqlite3.Connection) -> None:
    """source_ref 컬럼·부분 인덱스를 보장한다(milestones 가 없으면 아무것도 하지 않음)."""
    cols = {r[1] for r in conn.execute("PRAGMA table_info(milestones)").fetchall()}
    if not cols:
        return
    if "source_ref" not in cols:
        conn.execute("ALTER TABLE milestones ADD COLUMN source_ref TEXT")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_milestones_source_ref ON milestones(source_ref)"
                 " WHERE source_ref IS NOT NULL")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_milestones_type_date ON milestones(type, date DESC)")
