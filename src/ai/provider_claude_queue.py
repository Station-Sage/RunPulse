"""claude_queue provider 어댑터 — 큐 가용 여부 확인과 ProviderError 매핑 (DESIGN-V2-AI-CLAUDE-QUEUE §E2).

전역 LLM_PROVIDERS 에는 넣지 않는다(키 기반 체인과 별개). 코치 체인은 CLAUDE_QUEUE 를 선두 특수 원소로 다루고(`complete_coach`),
실패(ProviderError)면 기존 Groq/Gemini → 규칙 체인으로 내려간다. 요청 스레드에서 기다리지 않는다(백그라운드 스레드 전용).
"""
from __future__ import annotations

import json
import sqlite3

from src.ai import claude_queue, llm_budget
from src.ai.provider_common import ProviderError

MODEL_FOR_KIND = {"coach": "sonnet", "adherence": "sonnet", "insight_polish": "haiku", "narrative": "haiku",
                  "plan_draft": "opus", "deep_analysis": "opus"}
DEADLINE_FOR_KIND = {"coach": 120, "insight_polish": 60, "narrative": 90, "adherence": 90,
                     "plan_draft": 240, "deep_analysis": 240}
_QUOTA_REASONS = {"quota", "quota_sub", "claude_quota"}


def db_path_of(conn: sqlite3.Connection) -> str | None:
    for _seq, name, path in conn.execute("PRAGMA database_list").fetchall():
        if name == "main" and path:
            return path
    return None


def uid_of(conn: sqlite3.Connection) -> str | None:
    p = db_path_of(conn)
    return llm_budget.uid_from_db(p) if p else None


def available(conn: sqlite3.Connection, config: dict | None) -> bool:
    """설정 켜짐 + uid 허용 + 워커 하트비트 정상 + 일시정지 아님."""
    try:
        return claude_queue.status(conn, config, uid_of(conn))["available"]
    except Exception:  # noqa: BLE001 — 큐 테이블 없음 등 → 없는 것으로 취급
        return False


def complete(conn: sqlite3.Connection, config: dict | None, *, kind: str, prompt: str,
             model: str | None = None, deadline_sec: float | None = None, **kw) -> str:
    """큐로 한 번 호출해 텍스트를 반환. 사용 불가·실패는 ProviderError(reason)."""
    if not available(conn, config):
        raise ProviderError("no_key", detail="claude_queue unavailable")
    res = claude_queue.run_job(db_path_of(conn), kind=kind, model=model or MODEL_FOR_KIND.get(kind, "sonnet"),
                               prompt=prompt, deadline_sec=deadline_sec or DEADLINE_FOR_KIND.get(kind, 90), **kw)
    if res["ok"] and res["text"].strip():
        return res["text"]
    reason = res["reason"] or "empty"
    if reason in _QUOTA_REASONS:
        raise ProviderError("quota_sub", detail=reason)
    if reason in ("cq_timeout", "deadline"):
        raise ProviderError("cq_timeout", detail=reason)
    raise ProviderError("unexpected", detail=reason)


def try_complete(conn: sqlite3.Connection, config: dict | None, **kw) -> str | None:
    """complete 의 None 반환판 — 체인 폴백용."""
    try:
        return complete(conn, config, **kw)
    except ProviderError:
        return None


def complete_coach(conn, prompt: str, config, stats, on_tool, cq: dict) -> str:
    """코치 한 턴. cq: thread_key/ctx_hash/history/retire/should_cancel/on_progress/deadline_sec/system_ctx."""
    if conn is None:
        raise ProviderError("no_key")
    n_seen = 0
    outer = cq.get("on_progress")

    def progress(pj, partial):
        nonlocal n_seen
        try:
            names = list((json.loads(pj) or {}).get("tools", [])) if pj else []
        except (ValueError, AttributeError):
            names = []
        for n in names[n_seen:]:
            if on_tool is not None:
                on_tool(n)
        n_seen = max(n_seen, len(names))
        if stats is not None:
            stats["tool_calls"] = max(stats.get("tool_calls", 0), n_seen)
            stats["tool_names"] = [str(n) for n in names]
        if outer is not None:
            outer(pj, partial)
    kw = {k: cq[k] for k in ("thread_key", "ctx_hash", "history", "retire", "should_cancel", "system_ctx") if cq.get(k)}
    from src.mcp_remote.policy import LOCAL_ONLY_TOOLS, REMOTE_TOOLS
    return complete(conn, config, kind="coach", prompt=prompt, deadline_sec=cq.get("deadline_sec"),
                    tools="read", allowed_tools=sorted(REMOTE_TOOLS | LOCAL_ONLY_TOOLS), on_progress=progress, **kw)
