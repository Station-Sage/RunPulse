"""사용자 요청 심화 분석 (V2-AI-CLAUDE-QUEUE E5-d, deep_v1) — 오늘(또는 지정) 훈련을 opus 가 도구로 조회하며 해설한다.

결과는 ai_outputs(kind='deep', scope_key='act:<id>')에 입력 해시와 함께 저장한다(같은 입력이면 재호출 없음).
규칙 폴백은 없다: 큐 불가·실패면 reason 만 남기고 화면은 안내 문구를 보인다. 진행 단계·취소는 프로세스 메모리로 관리한다.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import sqlite3
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger(__name__)

KIND = "deep"
_TEMPLATE = Path(__file__).resolve().parents[1] / "ai" / "prompt_templates" / "deep_analysis.txt"
_MIN_LEN, _MAX_LEN = 80, 6000
_lock = threading.Lock()
_runs: dict[str, dict] = {}


def scope_key(activity_id: int) -> str:
    return f"act:{activity_id}"


def pick_activity_id(conn: sqlite3.Connection, activity_id: int | None = None) -> int | None:
    """지정 id(러닝 활동으로 존재해야 함) 또는 가장 최근 러닝 활동."""
    if activity_id:
        r = conn.execute("SELECT id FROM activity_summaries WHERE id=?", (int(activity_id),)).fetchone()
        return r[0] if r else None
    r = conn.execute("SELECT id FROM activity_summaries WHERE activity_type='running'"
                     " ORDER BY start_time DESC, id DESC LIMIT 1").fetchone()
    return r[0] if r else None


def build_prompt(conn: sqlite3.Connection, activity_id: int) -> str:
    from src.ai.ai_context_legacy import build_context, format_activity_context, format_context_text
    ctx_text = format_context_text(build_context(conn)) + "\n\n" + format_activity_context(conn, activity_id)
    return _TEMPLATE.read_text(encoding="utf-8").replace("{{CONTEXT}}", ctx_text)


def src_hash(prompt: str) -> str:
    return hashlib.sha256(prompt.encode()).hexdigest()[:16]


def split_output(text: str | None) -> dict | None:
    """응답 → {text, suggestions}. 너무 짧거나 길면 None."""
    t = (text or "").strip()
    sugg: list[str] = []
    m = re.search(r"```json\s*(\{.*?\})\s*```", t, re.S)
    if m:
        try:
            raw = json.loads(m.group(1)).get("suggestions") or []
            sugg = [s.strip() for s in raw if isinstance(s, str) and s.strip()][:3]
        except ValueError:
            pass
        t = (t[:m.start()] + t[m.end():]).strip()
    if not (_MIN_LEN <= len(t) <= _MAX_LEN):
        return None
    return {"text": t, "suggestions": sugg}


def get_cached(conn: sqlite3.Connection, activity_id: int) -> dict | None:
    r = conn.execute("SELECT body_json, created_at FROM ai_outputs WHERE kind=? AND scope_key=?",
                     (KIND, scope_key(activity_id))).fetchone()
    return {**json.loads(r[0]), "created_at": r[1]} if r else None


def _put(conn: sqlite3.Connection, activity_id: int, h: str, body: dict) -> None:
    conn.execute("INSERT OR REPLACE INTO ai_outputs(kind, scope_key, src_hash, body_json, created_at) VALUES (?,?,?,?,?)",
                 (KIND, scope_key(activity_id), h, json.dumps(body, ensure_ascii=False),
                  datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")))
    conn.commit()


def _progress(key: str):
    def cb(pj, _partial):
        try:
            names = list((json.loads(pj) or {}).get("tools", [])) if pj else []
        except (ValueError, AttributeError):
            names = []
        with _lock:
            if key in _runs:
                _runs[key]["tools"] = names
                _runs[key]["stage"] = "analyzing" if names else "thinking"
    return cb


def generate(conn: sqlite3.Connection, config: dict | None, activity_id: int, run_key: str | None = None) -> dict:
    """캐시(입력 해시 일치) → 큐 호출(opus, 도구 사용) → 검증 → 저장. 반환 {state: ready|failed, ...}."""
    from src.ai import claude_queue, provider_claude_queue as pcq
    from src.mcp_remote.policy import LOCAL_ONLY_TOOLS, REMOTE_TOOLS
    prompt = build_prompt(conn, activity_id)
    h = src_hash(prompt)
    row = conn.execute("SELECT src_hash FROM ai_outputs WHERE kind=? AND scope_key=?",
                       (KIND, scope_key(activity_id))).fetchone()
    if row and row[0] == h:
        return {"state": "ready", **get_cached(conn, activity_id)}
    if not pcq.available(conn, config):
        return {"state": "failed", "reason": "AI 큐를 사용할 수 없음"}
    cancelled = lambda: bool(run_key and _runs.get(run_key, {}).get("cancel"))  # noqa: E731
    res = claude_queue.run_job(pcq.db_path_of(conn), kind="deep_analysis", model=pcq.MODEL_FOR_KIND["deep_analysis"],
                               prompt=prompt, deadline_sec=pcq.DEADLINE_FOR_KIND["deep_analysis"], tools="read",
                               allowed_tools=sorted(REMOTE_TOOLS | LOCAL_ONLY_TOOLS), queue_wait=30,
                               on_progress=_progress(run_key) if run_key else None, should_cancel=cancelled)
    if res["reason"] == "cancelled":
        return {"state": "cancelled", "reason": "취소됨"}
    if not res["ok"]:
        return {"state": "failed", "reason": f"AI 호출 실패({res['reason']})"}
    body = split_output(res["text"])
    if body is None:
        return {"state": "failed", "reason": "응답 형식이 맞지 않아 폐기했어요"}
    _put(conn, activity_id, h, body)
    return {"state": "ready", **get_cached(conn, activity_id)}


def start_background(db_path: str, config: dict | None, activity_id: int) -> bool:
    """이미 진행 중이면 False."""
    with _lock:
        if db_path in _runs and _runs[db_path].get("state") == "running":
            return False
        _runs[db_path] = {"state": "running", "stage": "queued", "tools": [], "activity_id": activity_id,
                          "started": time.time(), "cancel": False}

    def _run() -> None:
        out: dict = {"state": "failed", "reason": "오류"}
        try:
            with sqlite3.connect(db_path, timeout=30) as c:
                c.row_factory = sqlite3.Row
                out = generate(c, config, activity_id, db_path)
        except Exception as e:  # noqa: BLE001
            log.warning("deep analysis failed", exc_info=True)
            out = {"state": "failed", "reason": f"오류: {str(e)[:80]}"}
        finally:
            with _lock:
                _runs[db_path].update(state=out.get("state", "failed"), reason=out.get("reason"), stage="done")
    threading.Thread(target=_run, daemon=True, name="deep-analysis").start()
    return True


def cancel(db_path: str) -> bool:
    with _lock:
        r = _runs.get(db_path)
        if r and r.get("state") == "running":
            r["cancel"] = True
            return True
    return False


def run_state(db_path: str) -> dict | None:
    with _lock:
        r = _runs.get(db_path)
        return None if r is None else {k: v for k, v in r.items() if k != "cancel"} | {"elapsed": int(time.time() - r["started"])}
