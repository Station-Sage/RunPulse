"""대회 캘린더 쓰기 서비스 (RC §2.3·2.4) — 등록·수정·취소. 복원·되돌리기는 race_calendar_state, 조회는 race_calendar_query.

모든 함수는 commit 하지 않는다(호출자 트랜잭션). 오류는 RaceError(code, http). A 대회는 race_goal_sync 로 목표 캐시를 같은 트랜잭션에서 맞춘다.
"""
from __future__ import annotations

import sqlite3

from src.services import race_calendar_query as q
from src.services import race_goal_sync as sync
from src.services.race_calendar_query import RaceError

EDITABLE = ("name", "race_date", "distance_km", "priority", "goal_type", "goal_value",
            "taper_days", "recovery_days", "note", "adapt_choice")
_PLAN_AFFECTING = ("race_date", "distance_km", "priority")
_INSERT = ("name", "race_date", "distance_km", "priority", "goal_type", "goal_value",
           "taper_days", "recovery_days", "origin", "note")

# RC-b 에서 race_plan_link 가 채운다. 적용된 배치를 되돌리고 되돌린 행 수를 반환.
_rollback_applied = lambda conn, race_id: 0  # noqa: E731


def add(conn: sqlite3.Connection, data: dict, *, as_goal: bool = False) -> dict:
    """대회 등록 → planned·unasked·none (과거 날짜 허용, RC-18). 다른 A 가 있으면 A_CONFLICT, 같은 날·거리면 DUPLICATE."""
    prio = data.get("priority", "B")
    if prio not in ("A", "B", "C"):
        raise RaceError("INVALID", "priority 는 A/B/C", http=400)
    if not data.get("name") or not data.get("race_date") or not data.get("distance_km"):
        raise RaceError("INVALID", "name·race_date·distance_km 필요", http=400)
    q.check_duplicate(conn, data["race_date"], data["distance_km"])
    if prio == "A":
        other = q.find_other_a(conn)
        if other:
            raise q.a_conflict(other)
    vals = {k: data.get(k) for k in _INSERT}
    vals["priority"], vals["origin"] = prio, data.get("origin") or "manual"
    cols = ",".join(vals)
    cur = conn.execute(f"INSERT INTO race_calendar ({cols}) VALUES ({','.join('?' * len(vals))})", tuple(vals.values()))
    if as_goal:
        conn.execute("UPDATE race_calendar SET adapt_choice='adapt', plan_state='applied' WHERE id=?", (cur.lastrowid,))
    return q.require(conn, cur.lastrowid)


def update(conn: sqlite3.Connection, race_id: int, changes: dict) -> dict:
    """수정. 적용된 대회의 날짜·거리·우선순위 변경은 stale. 목표 연결 대회는 A 유지 + 캐시 동기화(같은 트랜잭션)."""
    cur = q.require(conn, race_id)
    ch = {k: v for k, v in changes.items() if k in EDITABLE}
    if "priority" in ch and ch["priority"] not in ("A", "B", "C"):
        raise RaceError("INVALID", "priority 는 A/B/C", http=400)
    linked = q.is_goal_race(conn, race_id)
    if linked and ch.get("priority", "A") != "A":
        raise RaceError("GOAL_LINKED", "활성 목표에 연결된 대회는 B로 바꿀 수 없습니다")
    nd, nk = ch.get("race_date", cur["race_date"]), ch.get("distance_km", cur["distance_km"])
    if cur["status"] != "cancelled" and (nd, nk) != (cur["race_date"], cur["distance_km"]):
        q.check_duplicate(conn, nd, nk, exclude_id=race_id)
    if ch.get("priority") == "A" and cur["priority"] != "A" and cur["status"] != "cancelled":
        other = q.find_other_a(conn, race_id)
        if other:
            raise q.a_conflict(other)
    date_changed = nd != cur["race_date"]
    if cur["plan_state"] == "applied" and any(k in ch and ch[k] != cur[k] for k in _PLAN_AFFECTING):
        ch["plan_state"] = "stale"
    if ch:
        sets = ", ".join(f"{k}=?" for k in ch)
        conn.execute(f"UPDATE race_calendar SET {sets}, updated_at=datetime('now') WHERE id=?", (*ch.values(), race_id))
    if linked:
        sync.push_cache(conn, race_id, date_changed=date_changed)
    return q.require(conn, race_id)


def cancel(conn: sqlite3.Connection, race_id: int) -> dict:
    """삭제=취소. 이전 선택·적용 상태를 저장(RC-28)한 뒤 적용 배치를 되돌린다(RC-9). 활성 목표 대회는 거부."""
    cur = q.require(conn, race_id)
    if cur["status"] == "cancelled":
        raise RaceError("ALREADY_CANCELLED", "이미 취소된 대회입니다")
    if q.is_goal_race(conn, race_id):
        raise RaceError("GOAL_LINKED", "활성 목표에 연결된 대회는 취소할 수 없습니다. 목표를 먼저 변경하세요")
    conn.execute("UPDATE race_calendar SET cancel_prev_adapt_choice=?, cancel_prev_plan_state=? WHERE id=?",
                 (cur["adapt_choice"], cur["plan_state"], race_id))
    if cur["plan_state"] == "applied":
        _rollback_applied(conn, race_id)
    conn.execute("UPDATE race_calendar SET status='cancelled', plan_state='none', updated_at=datetime('now')"
                 " WHERE id=?", (race_id,))
    return q.require(conn, race_id)
