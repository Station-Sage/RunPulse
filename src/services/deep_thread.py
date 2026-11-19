"""심화 분석 → 코치 스레드 — 'AI 분석'을 코치 대화의 첫 답변으로 만든다 (opus 분석 결과 + 후속 칩)."""
from __future__ import annotations

import json
import logging
import sqlite3
import threading

from src.services import coach_async, coach_service, deep_analysis

log = logging.getLogger(__name__)
FIRST_MESSAGE = "오늘 훈련 상세 분석"
PROVIDER = "claude_queue"


def _stage_emitter(run: coach_async._Run):
    state = {"n": 0}

    def on_progress(pj, _partial) -> None:
        try:
            names = list((json.loads(pj) or {}).get("tools", [])) if pj else []
        except (ValueError, AttributeError):
            names = []
        state["n"] = max(state["n"], len(names))
        run.emit("stage", {"key": "analyzing" if names else "thinking",
                           "label": "기록을 살펴보는 중" if names else "생각하는 중",
                           "tool": names[-1] if names else None, "provider": PROVIDER})
    return on_progress


def _store(conn: sqlite3.Connection, thread_id: int, mid: int, out: dict, tool_calls: int) -> None:
    state = out.get("state")
    if state == "ready":
        sugg = [s for s in (out.get("suggestions") or []) if isinstance(s, str)][:3]
        engine = {"status": "ok", "provider": PROVIDER, "model": "opus", "tool_calls": tool_calls}
        conn.execute("UPDATE chat_messages SET content=?, ai_model=?, status='done', engine_json=?, followups_json=?,"
                     " as_of=date('now'), created_at=datetime('now') WHERE id=?",
                     (out["text"], PROVIDER, json.dumps(engine), json.dumps(sugg, ensure_ascii=False), mid))
    elif state == "cancelled":
        conn.execute("UPDATE chat_messages SET status='cancelled', content='' WHERE id=?", (mid,))
    else:
        engine = {"status": "fallback", "provider": "rule", "model": None, "tool_calls": tool_calls,
                  "fallback_reason": out.get("reason") or "failed"}
        conn.execute("UPDATE chat_messages SET status='error', content='', engine_json=? WHERE id=?",
                     (json.dumps(engine, ensure_ascii=False), mid))
    conn.execute("UPDATE chat_threads SET updated_at=datetime('now') WHERE id=?", (thread_id,))
    conn.commit()


def _execute(run: coach_async._Run, db_file: str, config: dict | None, thread_id: int, mid: int, aid: int) -> None:
    from src.ai import llm_budget
    conn = sqlite3.connect(db_file, timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("UPDATE chat_messages SET status='working' WHERE id=? AND status='pending'", (mid,))
        conn.commit()
        with llm_budget.scope(llm_budget.uid_from_db(db_file), "deep_analysis"):
            out = deep_analysis.generate(conn, config, aid, cancelled=run.cancel.is_set,
                                         on_progress=_stage_emitter(run))
        if run.cancel.is_set() and out.get("state") != "ready":
            out = {"state": "cancelled"}
        _store(conn, thread_id, mid, out, 0)
        for name, data in coach_async.replay_events(conn, mid):
            run.emit(name, data)
    except Exception:  # noqa: BLE001
        log.warning("deep thread 실패 message=%s", mid, exc_info=True)
        try:
            conn.execute("UPDATE chat_messages SET status='error', content='' WHERE id=?", (mid,))
            conn.commit()
        except sqlite3.Error:
            pass
        run.emit("error", {"status": "error", "reason": "internal", "attempts": []})
    finally:
        conn.close()
        run.finish()


def start(db_file: str, config: dict | None, activity_id: int) -> dict:
    """스레드를 만들고 백그라운드에서 분석을 돌린다. 반환 {thread, assistant_message}."""
    conn = sqlite3.connect(db_file, timeout=30)
    try:
        created = coach_service.create_thread(conn, FIRST_MESSAGE, config,
                                              context={"kind": "activity", "ref": deep_analysis.scope_key(activity_id)})
    finally:
        conn.close()
    thread, msg = created["thread"], created["assistant_message"]
    with coach_async._LOCK:
        coach_async._prune()
        run = coach_async._RUNS[msg["id"]] = coach_async._Run()
    args = (run, db_file, config, thread["id"], msg["id"], activity_id)
    if coach_async.INLINE:
        _execute(*args)
    else:
        threading.Thread(target=_execute, args=args, daemon=True, name=f"deep-{msg['id']}").start()
    return created
