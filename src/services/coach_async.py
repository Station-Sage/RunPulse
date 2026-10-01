"""Coach 비동기 답변 실행기 — 워커 스레드·메시지별 이벤트 로그·취소 플래그·SSE 직렬화 (design §6.2, §7.1).

POST가 pending 행을 만들고 start()로 워커를 띄우면, GET /coach/messages/:id/stream 이 이벤트 로그를 읽는다.
이벤트: stage(엔진 훅) · error(fallback 사유) · delta · evidence · done. 로그는 프로세스 메모리에만 있으므로
재시작·만료 후에는 DB 행에서 같은 이벤트를 다시 만든다(replay_events). 현재 provider는 비스트리밍이라
delta는 완성된 답변을 잘라 보낸 것이다.
"""
from __future__ import annotations

import json
import logging
import sqlite3
import threading
import time
from pathlib import Path

from src.services import coach_service

log = logging.getLogger(__name__)

CHUNK_CHARS = 40
PING_SECONDS = 15
KEEP_SECONDS = 600
MAX_RUNS = 200
INLINE = False  # 테스트 전용 — True면 start()가 워커 스레드 없이 호출 스레드에서 끝까지 실행한다.


class _Run:
    def __init__(self) -> None:
        self.events: list[tuple[int, str, dict]] = []
        self.cond = threading.Condition()
        self.done = False
        self.cancel = threading.Event()
        self.finished_at = 0.0

    def emit(self, name: str, data: dict) -> None:
        with self.cond:
            self.events.append((len(self.events) + 1, name, data))
            self.cond.notify_all()

    def finish(self) -> None:
        with self.cond:
            self.done = True
            self.finished_at = time.monotonic()
            self.cond.notify_all()


_RUNS: dict[int, _Run] = {}
_LOCK = threading.Lock()


def _prune() -> None:
    now = time.monotonic()
    for mid in [m for m, r in _RUNS.items() if r.done and now - r.finished_at > KEEP_SECONDS]:
        del _RUNS[mid]
    while len(_RUNS) > MAX_RUNS:
        done = [m for m, r in _RUNS.items() if r.done]
        if not done:
            return
        del _RUNS[done[0]]


def source_text(conn: sqlite3.Connection, assistant_id: int) -> tuple[int, str, str | None] | None:
    """assistant 행 → (thread_id, 답해야 할 사용자 질문, chip_id). 재생성이면 부모 체인을 따라 올라간다."""
    cur = assistant_id
    for _ in range(20):
        row = conn.execute("SELECT thread_id, parent_message_id, role FROM chat_messages WHERE id = ?",
                           (cur,)).fetchone()
        if not row:
            return None
        thread_id, parent, role = row
        if role == "user":
            u = conn.execute("SELECT content, chip_id FROM chat_messages WHERE id = ?", (cur,)).fetchone()
            return thread_id, u[0], u[1]
        if parent is None:
            u = conn.execute("SELECT content, chip_id FROM chat_messages WHERE thread_id = ? AND id < ?"
                             " AND role = 'user' ORDER BY id DESC LIMIT 1", (thread_id, cur)).fetchone()
            return (thread_id, u[0], u[1]) if u else None
        cur = parent
    return None


def _attempts(conn: sqlite3.Connection, message_id: int) -> tuple[str | None, list[dict]]:
    from src.services.coach_engine_health import parse_engine
    row = conn.execute("SELECT engine_json FROM chat_messages WHERE id = ?", (message_id,)).fetchone()
    eng = parse_engine(row[0] if row else None) or {}
    out = [{"provider": a.get("provider"), "model": a.get("model"),
            "status": "ok" if a.get("ok") else (a.get("reason") or "failed"), "ms": a.get("latency_ms")}
           for a in eng.get("attempts") or []]
    return eng.get("fallback_reason"), out


def replay_events(conn: sqlite3.Connection, message_id: int) -> list[tuple[str, dict]]:
    """완료된 assistant 행 → delta·evidence·done(+fallback이면 앞에 error) 이벤트 목록(stage 제외)."""
    view = coach_service.get_message(conn, message_id)
    if view is None:
        return []
    status = view["status"]
    if status == "error":
        return [("error", {"status": "error", "reason": "internal", "attempts": []})]
    out: list[tuple[str, dict]] = []
    if status == "fallback":
        reason, attempts = _attempts(conn, message_id)
        out.append(("error", {"status": "fallback", "reason": reason, "attempts": attempts}))
    text = view["content"] or ""
    out += [("delta", {"text": text[i:i + CHUNK_CHARS]}) for i in range(0, len(text), CHUNK_CHARS)]
    if view["evidence"]:
        out.append(("evidence", view["evidence"]))
    engine = view["engine"]
    out.append(("done", {
        "status": status,
        "engine": {"provider": engine.get("provider"), "model": engine.get("model"), "label": engine.get("label"),
                   "tool_calls": 0},
        "as_of": {"basis": "generated", "at": view.get("as_of")},
        "followups": view["followups"],
    }))
    return out


def _execute(run: _Run, db_file: str, config: dict | None, thread_id: int, assistant_id: int,
             user_text: str, chip_id: str | None) -> None:
    conn = sqlite3.connect(db_file)
    try:
        coach_service.generate_reply(conn, thread_id, assistant_id, user_text, config=config, chip_id=chip_id,
                                     on_event=run.emit, cancelled=run.cancel.is_set)
        for name, data in replay_events(conn, assistant_id):
            run.emit(name, data)
    except Exception:
        log.warning("coach 워커 실패 message=%s", assistant_id, exc_info=True)
        run.emit("error", {"status": "error", "reason": "internal", "attempts": []})
    finally:
        conn.close()
        run.finish()


def start(db_file: str | Path, config: dict | None, assistant_id: int, mode: str = "ai") -> bool:
    """pending assistant 행의 답변 생성을 시작한다. mode='rule'이면 AI 호출 없이 규칙 답변만. 이미 돌고 있으면 False."""
    conn = sqlite3.connect(str(db_file))
    try:
        src = source_text(conn, assistant_id)
    finally:
        conn.close()
    if src is None:
        return False
    thread_id, user_text, chip_id = src
    if mode == "rule":
        config = {**(config or {}), "ai": {**(config or {}).get("ai", {}), "provider": "rule"}}
    with _LOCK:
        if assistant_id in _RUNS and not _RUNS[assistant_id].done:
            return False
        _prune()
        run = _RUNS[assistant_id] = _Run()
    args = (run, str(db_file), config, thread_id, assistant_id, user_text, chip_id)
    if INLINE:
        _execute(*args)
    else:
        threading.Thread(target=_execute, args=args, daemon=True, name=f"coach-{assistant_id}").start()
    return True


def cancel(db_file: str | Path, assistant_id: int) -> str | None:
    """진행 중이면 취소 플래그를 세운다. 돌고 있지 않은데 pending/working이면 cancelled로 마감한다. 상태를 반환."""
    run = _RUNS.get(assistant_id)
    if run is not None and not run.done:
        run.cancel.set()
        return "cancelled"
    conn = sqlite3.connect(str(db_file))
    try:
        row = conn.execute("SELECT status FROM chat_messages WHERE id = ? AND role = 'assistant'",
                           (assistant_id,)).fetchone()
        if row is None:
            return None
        if row[0] in coach_service.PENDING_STATUSES:
            conn.execute("UPDATE chat_messages SET status = 'cancelled' WHERE id = ?", (assistant_id,))
            conn.commit()
            return "cancelled"
        return row[0]
    finally:
        conn.close()


def sse(event_id: int, name: str, data) -> str:
    return f"id: {event_id}\nevent: {name}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def stream(db_file: str | Path, assistant_id: int, last_event_id: int = 0, ping_seconds: float = PING_SECONDS):
    """SSE 문자열 제너레이터. 로그가 있으면 실시간으로, 없으면 DB 행에서 복원해 보낸다."""
    run = _RUNS.get(assistant_id)
    if run is None:
        yield from _stream_stored(db_file, assistant_id, last_event_id)
        return
    idx = 0
    while True:
        with run.cond:
            while idx >= len(run.events) and not run.done:
                if not run.cond.wait(timeout=ping_seconds):
                    break
            batch = run.events[idx:]
            finished = run.done and idx + len(batch) >= len(run.events)
        if not batch:
            if finished:
                return
            yield ": ping\n\n"
            continue
        idx += len(batch)
        for eid, name, data in batch:
            if eid > last_event_id:
                yield sse(eid, name, data)
        if finished:
            return


def _stream_stored(db_file: str | Path, assistant_id: int, last_event_id: int):
    conn = sqlite3.connect(str(db_file))
    try:
        view = coach_service.get_message(conn, assistant_id)
        if view is None:
            return
        if view["status"] in coach_service.PENDING_STATUSES:
            conn.execute("UPDATE chat_messages SET status = 'error' WHERE id = ?", (assistant_id,))
            conn.commit()
            events = [("error", {"status": "error", "reason": "interrupted", "attempts": []})]
        else:
            events = replay_events(conn, assistant_id)
    finally:
        conn.close()
    for i, (name, data) in enumerate(events, start=1):
        if i > last_event_id:
            yield sse(i, name, data)
