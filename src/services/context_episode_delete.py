"""컨텍스트 에피소드 삭제 연쇄 (NEW-18·28) — 한 트랜잭션, commit 은 호출자.

질병: plan_adjustments 의 질병 흔적 익명화 + 질병만이 근거인 proposed 철회 + ai_cache 전체 삭제 +
선택한 대화 스레드 메시지 삭제(+빈 스레드 정리) + thread_id 없는 메시지 삭제. 여행·고도는 이력을 보존한다.
"""
from __future__ import annotations

import json
import sqlite3

from src.ai import ai_cache
from src.services.plan_adj_flag import sync_adj_flag

_GENERIC = "컨디션 신호"


def _scrub_signals(raw: str | None) -> tuple[str, bool]:
    try:
        items = json.loads(raw or "[]")
    except (ValueError, TypeError):
        return raw or "[]", False
    hit = False
    for it in items:
        if isinstance(it, dict) and it.get("signal") == "illness":
            it.update(signal="condition", value=_GENERIC, detail=None)
            hit = True
    return json.dumps(items, ensure_ascii=False), hit


def _scrub_reasons(raw: str | None) -> tuple[str, bool]:
    try:
        items = json.loads(raw or "[]")
    except (ValueError, TypeError):
        return raw or "[]", False
    hit = False
    for it in items:
        if isinstance(it, dict) and it.get("key") == "illness":
            it.clear()
            it.update(key="condition", text=_GENERIC)
            hit = True
    return json.dumps(items, ensure_ascii=False), hit


def _anonymize_adjustments(conn) -> set[int]:
    touched: set[int] = set()
    rows = conn.execute("SELECT id, workout_id, source, decision, signals_json, reasons_json FROM plan_adjustments"
                        " WHERE source='illness' OR signals_json LIKE '%illness%' OR reasons_json LIKE '%illness%'").fetchall()
    for rid, wid, source, decision, sj, rj in rows:
        sj2, h1 = _scrub_signals(sj)
        rj2, h2 = _scrub_reasons(rj)
        if source == "illness" and decision == "proposed":
            conn.execute("UPDATE plan_adjustments SET decision='reverted', decided_at=datetime('now'),"
                         " signals_json=?, reasons_json=?, source='readiness', updated_at=datetime('now') WHERE id=?",
                         (sj2, rj2, rid))
            touched.add(wid)
        elif h1 or h2 or source == "illness":
            conn.execute("UPDATE plan_adjustments SET signals_json=?, reasons_json=?,"
                         " source=CASE WHEN source='illness' THEN 'readiness' ELSE source END,"
                         " updated_at=datetime('now') WHERE id=?", (sj2, rj2, rid))
    return touched


def _delete_chat(conn, thread_ids) -> int:
    n = 0
    ids = sorted({int(t) for t in thread_ids})
    if ids:
        ph = ",".join("?" * len(ids))
        n += conn.execute(f"DELETE FROM chat_messages WHERE thread_id IN ({ph})", ids).rowcount
    n += conn.execute("DELETE FROM chat_messages WHERE thread_id IS NULL").rowcount
    conn.execute("DELETE FROM chat_threads WHERE id NOT IN (SELECT DISTINCT thread_id FROM chat_messages"
                 " WHERE thread_id IS NOT NULL)")
    return n


def delete_episode(conn: sqlite3.Connection, episode_id: int, *, chat_thread_ids=()) -> dict | None:
    """없으면 None. 질병이면 연쇄 삭제 후 요약 dict 반환."""
    row = conn.execute("SELECT kind FROM context_episodes WHERE id=?", (episode_id,)).fetchone()
    if row is None:
        return None
    kind = row[0]
    out = {"kind": kind, "chat_deleted": 0}
    conn.execute("DELETE FROM context_episodes WHERE id=?", (episode_id,))
    if kind == "illness":
        sync_adj_flag(conn, _anonymize_adjustments(conn))
        ai_cache.clear_all_no_commit(conn)
        out["chat_deleted"] = _delete_chat(conn, chat_thread_ids)
    return out
