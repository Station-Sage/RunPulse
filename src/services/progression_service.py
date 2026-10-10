"""품질 세션 사다리 단계 저장·갱신 서비스(U16l) — progression.py 순수 함수와 plan_progression 테이블을 잇는다."""
from __future__ import annotations

import sqlite3
from datetime import date

from src.training import progression as PG


_LABEL = {"overperformed": "over", "underperformed": "under", "skipped": "missed"}   # R5 라벨 → 사다리 라벨


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


def recompute(conn: sqlite3.Connection, goal_id: int, qtype: str) -> int:
    """v2 규칙 주의 같은 유형 세션 라벨 이력 전체를 처음부터 접어 단계를 다시 계산·저장한다(멱등 — 재매칭에도 중복 승급 없음)."""
    from src.training.goals import effective_rules_version
    rows = conn.execute(
        "SELECT p.date, o.outcome_label FROM planned_workouts p JOIN session_outcomes o ON o.planned_id=p.id "
        "WHERE p.workout_type=? AND o.outcome_label IS NOT NULL ORDER BY p.date, p.id", (qtype,)).fetchall()
    labels: list[str] = []
    step, reason = 0, "no_history"
    for d, lab in rows:
        try:
            if effective_rules_version(conn, goal_id, date.fromisoformat(d)) < 2:
                continue
        except ValueError:
            continue
        labels.append(_LABEL.get(lab, lab))
        step, reason = PG.next_step(qtype, step, labels)
    conn.execute("INSERT INTO plan_progression(goal_id, qtype, step, updated_at, reason) "
                 "VALUES(?,?,?,datetime('now'),?) ON CONFLICT(goal_id, qtype) DO UPDATE SET "
                 "step=excluded.step, updated_at=excluded.updated_at, reason=excluded.reason",
                 (goal_id, qtype, step, reason))
    return step


def on_outcome(conn: sqlite3.Connection, planned_id: int) -> None:
    """결과가 저장된 계획 행이 품질 유형이면 활성 목표의 그 유형 사다리를 다시 계산한다. 실패는 삼킨다(결과 저장을 막지 않음)."""
    try:
        r = conn.execute("SELECT workout_type FROM planned_workouts WHERE id=?", (planned_id,)).fetchone()
        if not r or r[0] not in PG.LADDERS:
            return
        from src.training.goals import get_active_goal
        g = get_active_goal(conn)
        if g:
            recompute(conn, g["id"], r[0])
    except sqlite3.Error:
        return
