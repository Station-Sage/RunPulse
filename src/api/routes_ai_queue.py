"""`/api/v1/ai/queue*` — Claude 큐 상태 조회·핑 (V2-AI-CLAUDE-QUEUE E1). 핑은 쓰기라 Origin 관문 대상."""
from __future__ import annotations

import sqlite3

from src.ai import claude_queue as cq
from src.ai_worker import queue_store as qs
from src.utils.config import load_config
from src.utils.user_context import db_path, get_current_user_id

from . import api_bp, api_error, api_ok

PING_DEADLINE_SEC = 25.0


def _status(uid):
    dpath = db_path()
    if not dpath.exists():
        return None
    conn = qs.connect(dpath)
    try:
        return cq.status(conn, load_config(user_id=uid), uid)
    finally:
        conn.close()


@api_bp.get("/ai/queue")
def get_ai_queue():
    st = _status(get_current_user_id())
    if st is None:
        return api_error("NOT_FOUND", "running.db 없음", 503)
    return api_ok(st)


@api_bp.get("/ai/queue/status")
def get_ai_queue_status():
    uid = get_current_user_id()
    dpath = db_path()
    if not dpath.exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)
    conn = qs.connect(dpath)
    try:
        st = cq.status(conn, load_config(user_id=uid), uid)
        w = conn.execute("SELECT heartbeat_at, active_jobs, cli_version, paused_until, last_error"
                         " FROM ai_worker_state ORDER BY heartbeat_at DESC LIMIT 1").fetchone()
        jobs = {r[0]: r[1] for r in conn.execute("SELECT state, COUNT(*) FROM ai_jobs"
                                                 " WHERE state IN ('queued','running') GROUP BY state")}
        last = conn.execute("SELECT kind, error_reason, finished_at FROM ai_jobs WHERE state='failed'"
                            " ORDER BY finished_at DESC LIMIT 1").fetchone()
    finally:
        conn.close()
    return api_ok({**st, "worker": dict(w) if w else None, "jobs": jobs,
                   "last_error": dict(last) if last else None})


@api_bp.post("/ai/queue/ping")
def ping_ai_queue():
    uid = get_current_user_id()
    st = _status(uid)
    if st is None:
        return api_error("NOT_FOUND", "running.db 없음", 503)
    if not st["enabled"]:
        return api_ok({**st, "ok": False, "reason": "disabled"})
    if not st["worker_up"]:
        return api_ok({**st, "ok": False, "reason": "worker_down"})
    r = cq.run_job(db_path(), kind="ping", model="haiku", prompt="Reply with exactly: pong",
                   deadline_sec=PING_DEADLINE_SEC)
    return api_ok({**st, "ok": r["ok"], "reason": r["reason"], "text": r["text"][:80],
                   "queue_ms": r["queue_ms"]})
