"""사용자 사건·러닝 기록 마일스톤 1회 백필 (ADR-057) — 기존 출처 행에서 다시 만든다. 멱등(재실행 안전).

날짜: 대회 완주 = 대회일, 목표 설정·대회 등록·재계획 = created_at(UTC) 의 현지 날짜, 질병/부상 = 시작·종료일,
최장거리·연속 주 = 사건일. 목표 수정(goal_changed)은 변경 이력이 저장돼 있지 않아 백필하지 않는다.
취소된 목표는 뒤에 다른 목표가 생긴 경우(= 새 목표로 교체)만 포함 — 사용자 취소와 구분할 수 없어 근사한다.
누적 거리·PB 는 기존 동기화 탐지 그대로(여기서 다시 돌리지 않음). commit 은 호출자(run_backfill 은 dry_run 이면 롤백).
"""
from __future__ import annotations

import sqlite3

from src.services import milestone_events as ev
from src.services import milestone_hooks as H
from src.services import milestone_running as R


def _counts(conn: sqlite3.Connection) -> dict[str, int]:
    return dict(conn.execute("SELECT type, COUNT(*) FROM milestones GROUP BY type").fetchall())


def _rows(conn: sqlite3.Connection, sql: str) -> list[tuple]:
    try:
        return conn.execute(sql).fetchall()
    except sqlite3.OperationalError:   # 구 스키마(출처 테이블 없음)
        return []


def backfill(conn: sqlite3.Connection) -> dict[str, int]:
    """모든 출처를 훑어 마일스톤을 채운다. 반환 = 종류별 증감(after - before)."""
    before = _counts(conn)
    off = ev.user_offset(conn)
    for (aid,) in _rows(conn, "SELECT activity_id FROM race_results ORDER BY activity_id"):
        H.on_race_result(conn, aid)
    for gid, created in _rows(conn, "SELECT g.id, g.created_at FROM goals g WHERE g.status IN ('active','completed')"
                                    " OR (g.status='cancelled' AND EXISTS (SELECT 1 FROM goals n WHERE n.id > g.id))"
                                    " ORDER BY g.id"):
        H.on_goal_set(conn, gid, ev.local_date_of(conn, created, off))
    for rid, created in _rows(conn, "SELECT id, created_at FROM race_calendar WHERE status != 'cancelled' ORDER BY id"):
        H.on_race_registered(conn, rid, ev.local_date_of(conn, created, off))
    for (eid,) in _rows(conn, "SELECT id FROM context_episodes WHERE kind IN ('illness','injury') ORDER BY id"):
        H.on_episode(conn, eid)
    for pid, created in _rows(conn, "SELECT id, created_at FROM plan_replans WHERE status='applied' ORDER BY id"):
        H.on_replan(conn, pid, ev.local_date_of(conn, created, off))
    R.detect_longest_runs(conn)
    R.detect_streaks(conn, ev.today_local(conn))
    ev.prune_orphans(conn)
    after = _counts(conn)
    return {k: after.get(k, 0) - before.get(k, 0) for k in sorted(set(before) | set(after))
            if after.get(k, 0) != before.get(k, 0)}


def run_backfill(conn: sqlite3.Connection, *, apply: bool = False) -> dict[str, int]:
    """한 트랜잭션에서 v49 컬럼 보장 + backfill. apply=False 면 롤백(쓰기 없음)."""
    from src.db_schema_v49 import ensure_v49
    if conn.in_transaction:
        conn.commit()
    conn.execute("BEGIN IMMEDIATE")
    try:
        ensure_v49(conn)
        out = backfill(conn)
    except Exception:
        conn.rollback()
        raise
    if apply:
        conn.commit()
    else:
        conn.rollback()
    return out
