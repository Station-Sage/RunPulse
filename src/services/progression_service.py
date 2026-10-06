"""품질 세션 사다리 단계 저장·갱신 서비스(U16l) — progression.py 순수 함수와 plan_progression 테이블을 잇는다."""
from __future__ import annotations

import sqlite3

from src.training import progression as PG


def get_step(conn: sqlite3.Connection, goal_id: int, qtype: str) -> int:
    """저장된 단계, 없거나 테이블이 없으면 0."""
    try:
        r = conn.execute("SELECT step FROM plan_progression WHERE goal_id=? AND qtype=?", (goal_id, qtype)).fetchone()
    except sqlite3.OperationalError:
        return 0
    return int(r[0]) if r else 0


def advance(conn: sqlite3.Connection, goal_id: int, qtype: str, labels: list[str]) -> int:
    """labels 로 다음 단계를 계산해 저장하고 돌려준다."""
    step, reason = PG.next_step(qtype, get_step(conn, goal_id, qtype), labels)
    conn.execute("INSERT INTO plan_progression(goal_id, qtype, step, updated_at, reason) "
                 "VALUES(?,?,?,datetime('now'),?) ON CONFLICT(goal_id, qtype) DO UPDATE SET "
                 "step=excluded.step, updated_at=excluded.updated_at, reason=excluded.reason",
                 (goal_id, qtype, step, reason))
    return step
