"""대회 상태 전이 — 복원(restore, §2.12)·되돌리기(reopen, §2.13).

한 트랜잭션(commit 은 호출자): goal_link 변경 → 기존 A 강등 → 상태 전이(+재적용) 순서. 재적용은 savepoint 로 감싸
실패해도 복원은 유지되고 adapt·stale 이 된다(replan_applied=False + reason).
"""
from __future__ import annotations

import sqlite3

from src.services import race_calendar_query as q
from src.services import race_goal_sync as sync
from src.services.race_calendar_query import RaceError

# RC-b 에서 race_plan_link 가 채운다. (적용 여부, 사유코드) 반환.
_reapply = lambda conn, race_id, today: (False, "NOT_AVAILABLE")  # noqa: E731


def _resolve_a_conflict(conn, race_id: int, demote_existing_a: bool, goal_link: dict | None) -> int | None:
    """기존 A 충돌을 정리. 활성 목표를 옮겨야 하면 그 goal_id 를 돌려준다(연결은 상태 전이 뒤에 호출자가 수행)."""
    other = q.find_other_a(conn, race_id)
    if not other:
        return None
    if other["status"] == "done" and not other["active_goal_id"]:
        return None  # 끝난 이전 A 는 공존(§2.2)
    if other["active_goal_id"]:
        if not goal_link:
            raise q.a_conflict(other)
        if goal_link.get("race_id", race_id) != race_id:
            raise RaceError("GOAL_LINK_TARGET", "목표 연결 대상은 복원하려는 대회여야 합니다")
        # 부분 유니크(planned A 1건) 때문에 복원 전에 기존 A 를 비워야 한다 — 목표 연결은 전이 뒤 link_goal 이 되살린다.
        conn.execute("UPDATE goals SET race_id=NULL WHERE id=?", (other["active_goal_id"],))
        sync.demote_a(conn, other["id"])
        return other["active_goal_id"]
    if not demote_existing_a:
        raise q.a_conflict(other)
    sync.demote_a(conn, other["id"])
    return None


def restore(conn: sqlite3.Connection, race_id: int, today: str, *, confirm_past: bool = False,
            demote_existing_a: bool = False, goal_link: dict | None = None) -> dict:
    """취소된 대회를 되살린다. 과거 날짜는 confirm_past 필요(done), 미래는 planned. cancel_prev_* 로 선택·상태 복구."""
    r = q.require(conn, race_id)
    if r["status"] != "cancelled":
        raise RaceError("NOT_CANCELLED", "취소된 대회만 복원할 수 있습니다")
    past = r["race_date"] < today
    if past and not confirm_past:
        raise RaceError("CONFIRM_PAST", "지난 날짜의 대회입니다. 확인 후 복원하세요")
    new_status = "done" if past else "planned"
    if new_status == "planned":
        q.check_duplicate(conn, r["race_date"], r["distance_km"], exclude_id=race_id)
    link_gid = _resolve_a_conflict(conn, race_id, demote_existing_a, goal_link) if r["priority"] == "A" else None
    adapt = r["cancel_prev_adapt_choice"] or "unasked"
    state = r["cancel_prev_plan_state"] or "none"
    linked = link_gid is not None or q.is_goal_race(conn, race_id)
    if linked:
        adapt, state = "adapt", "applied"
    elif state == "applied":
        state = "none"
    conn.execute("UPDATE race_calendar SET status=?, adapt_choice=?, plan_state=?, cancel_prev_adapt_choice=NULL,"
                 " cancel_prev_plan_state=NULL, updated_at=datetime('now') WHERE id=?",
                 (new_status, adapt, state, race_id))
    if link_gid is not None:
        sync.link_goal(conn, link_gid, race_id)
    out = {"replan_applied": None, "reason": None}
    if r["cancel_prev_plan_state"] == "applied" and not linked and not past:
        conn.execute("SAVEPOINT race_reapply")
        try:
            ok, reason = _reapply(conn, race_id, today)
        except Exception:  # noqa: BLE001 — 재적용 실패가 복원을 막지 않는다(RC-47)
            ok, reason = False, "ERROR"
        if ok:
            conn.execute("RELEASE race_reapply")
            conn.execute("UPDATE race_calendar SET plan_state='applied' WHERE id=?", (race_id,))
        else:
            conn.execute("ROLLBACK TO race_reapply")
            conn.execute("RELEASE race_reapply")
            conn.execute("UPDATE race_calendar SET adapt_choice='adapt', plan_state='stale' WHERE id=?", (race_id,))
        out = {"replan_applied": ok, "reason": None if ok else reason}
    return {**q.require(conn, race_id), **{"restore": out}}


def reopen(conn: sqlite3.Connection, race_id: int, today: str, *, demote_existing_a: bool = False,
           goal_link: dict | None = None) -> dict:
    """확인 필요(done·대회일≥오늘) 행을 planned·unasked·none 으로 되돌린다."""
    r = q.require(conn, race_id)
    if not q.is_needs_review(r, today):
        raise RaceError("NOT_NEEDS_REVIEW", "확인 필요 상태의 대회만 되돌릴 수 있습니다")
    q.check_duplicate(conn, r["race_date"], r["distance_km"], exclude_id=race_id)
    link_gid = _resolve_a_conflict(conn, race_id, demote_existing_a, goal_link) if r["priority"] == "A" else None
    linked = link_gid is not None or q.is_goal_race(conn, race_id)
    conn.execute("UPDATE race_calendar SET status='planned', adapt_choice=?, plan_state=?, updated_at=datetime('now')"
                 " WHERE id=?", ("adapt" if linked else "unasked", "applied" if linked else "none", race_id))
    if link_gid is not None:
        sync.link_goal(conn, link_gid, race_id)
    return q.require(conn, race_id)
