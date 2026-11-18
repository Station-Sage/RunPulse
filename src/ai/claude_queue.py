"""claude_queue 앱 측 클라이언트 — 큐에 job 을 넣고 결과를 폴링한다 (flask 의존 없음)."""
from __future__ import annotations

import json
import time

from src.ai_worker import queue_store as qs

QUEUE_WAIT_SEC = 10.0
POLL_SEC = 0.25


def enabled_for(config: dict | None, uid: str | None) -> bool:
    cfg = ((config or {}).get("ai") or {}).get("claude_queue") or {}
    return bool(cfg.get("enabled")) and bool(uid) and uid in (cfg.get("uids") or [])


def status(conn, config: dict | None, uid: str | None) -> dict:
    """{enabled, worker_up, available} — worker_up 은 하트비트·일시정지 기준."""
    en = enabled_for(config, uid)
    up = qs.worker_available(conn)
    return {"enabled": en, "worker_up": up, "available": en and up}


def run_job(db_path, *, kind: str, model: str, prompt: str, deadline_sec: float, system_ctx: str | None = None,
            tools: str = "none", allowed_tools: list[str] | None = None, queue_wait: float = QUEUE_WAIT_SEC,
            sleep=time.sleep) -> dict:
    """job 을 넣고 끝날 때까지 기다린다. {ok, text, reason, job_id, queue_ms}.

    queue_wait 안에 아무도 집지 않으면 취소하고 reason=cq_timeout. 요청 스레드에서는 짧은 마감으로만 쓴다.
    """
    conn = qs.connect(db_path)
    try:
        inp = {"prompt": prompt}
        if allowed_tools:
            inp["allowed_tools"] = allowed_tools
        jid = qs.enqueue(conn, kind=kind, model=model, input_json=json.dumps(inp, ensure_ascii=False),
                         system_ctx=system_ctx, tools=tools, ttl_sec=int(queue_wait + deadline_sec + 30))
        start = time.monotonic()
        while True:
            row = conn.execute("SELECT state, result_text, error_reason, queue_ms FROM ai_jobs WHERE id=?",
                               (jid,)).fetchone()
            state = row["state"]
            if state == "done":
                return {"ok": True, "text": row["result_text"] or "", "reason": None, "job_id": jid,
                        "queue_ms": row["queue_ms"]}
            if state in qs.TERMINAL:
                return {"ok": False, "text": "", "reason": row["error_reason"] or state, "job_id": jid,
                        "queue_ms": row["queue_ms"]}
            waited = time.monotonic() - start
            if (state == "queued" and waited > queue_wait) or waited > queue_wait + deadline_sec:
                conn.execute("UPDATE ai_jobs SET cancel_requested=1 WHERE id=?", (jid,))
                conn.execute("UPDATE ai_jobs SET state='cancelled', error_reason='cq_timeout', finished_at=?"
                             " WHERE id=? AND state='queued'", (qs.now_iso(), jid))
                return {"ok": False, "text": "", "reason": "cq_timeout", "job_id": jid, "queue_ms": None}
            sleep(POLL_SEC)
    finally:
        conn.close()
