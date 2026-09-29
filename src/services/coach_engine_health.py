"""Coach 엔진 상태 — 메시지별 엔진 라벨, 최근 20개 집계(H0 배너), GET /coach/engine 페이로드.

외부 provider를 따로 probe하지 않는다 — 저장된 chat_messages.engine_json만 집계한다(design §7.3).
"""
from __future__ import annotations

import json
import sqlite3

from src.ai.chat_context_scope import scope_catalog
from src.ai.chat_engine_result import build_chain
from src.ai.provider_common import LLM_PROVIDERS, REASON_LABELS, api_key_for, model_for
from src.services.coach_consent import get_consent

WINDOW = 20
DEGRADED_AFTER = 3
_PROVIDER_NAMES = {"gemini": "Gemini", "groq": "Groq", "openai": "OpenAI", "claude": "Claude"}


def model_label(provider: str, model: str | None) -> str:
    name = _PROVIDER_NAMES.get(provider, provider)
    if not model:
        return name
    if model.startswith(provider + "-"):
        return f"{name} {model[len(provider) + 1:].replace('-', ' ').title()}"
    return f"{name} · {model}"


def reason_label(reason: str | None) -> str:
    return REASON_LABELS.get(reason or "", reason or "알 수 없음")


def engine_label(status: str, provider: str | None, model: str | None, tool_calls: int, reason: str | None) -> str:
    if status == "ok":
        base = model_label(provider or "", model)
        return f"{base} · 조회 {tool_calls}회" if tool_calls else base
    if status == "fallback":
        return "기본 규칙 답변"
    if status == "rule_only":
        return "규칙 답변 (AI 미설정)"
    if status == "rule_by_choice":
        return "규칙 답변 (AI 끔)"
    if status == "error":
        return f"답변을 만들지 못했어요 ({reason_label(reason)})"
    if status == "cancelled":
        return "중단됨"
    return "규칙 답변"


def parse_engine(engine_json: str | None) -> dict | None:
    try:
        data = json.loads(engine_json) if engine_json else None
    except (TypeError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def message_engine_view(engine_json: str | None, ai_model: str | None) -> dict:
    """저장된 메시지 → {status, label, provider, model, reason}. engine_json이 없는 옛 메시지는 ai_model로 추정."""
    data = parse_engine(engine_json)
    if data is None:
        if ai_model and ai_model != "rule":
            return {"status": "ok", "label": model_label(ai_model, None), "provider": ai_model,
                    "model": None, "reason": None}
        return {"status": "legacy_rule", "label": "규칙 답변", "provider": "rule", "model": None, "reason": None}
    status = data.get("status", "ok")
    reason = data.get("fallback_reason")
    return {
        "status": status, "provider": data.get("provider"), "model": data.get("model"), "reason": reason,
        "label": engine_label(status, data.get("provider"), data.get("model"), data.get("tool_calls", 0), reason),
    }


def health_summary(conn: sqlite3.Connection) -> dict:
    """최근 20개 assistant 메시지 집계 — 연속 fallback ≥3이면 degraded(H0 배너), 성공 1회로 해제."""
    rows = conn.execute(
        "SELECT engine_json, created_at FROM chat_messages"
        " WHERE role = 'assistant' AND engine_json IS NOT NULL ORDER BY id DESC LIMIT ?", (WINDOW,),
    ).fetchall()
    consecutive, counting = 0, True
    last_ok_at, last_error = None, None
    for engine_json, created_at in rows:
        eng = parse_engine(engine_json) or {}
        status = eng.get("status")
        if status == "ok" and last_ok_at is None:
            last_ok_at = created_at
        if status == "fallback":
            if last_error is None:
                first = (eng.get("attempts") or [{}])[0]
                last_error = {"provider": first.get("provider"), "model": first.get("model"),
                              "status": first.get("http_status"), "reason": eng.get("fallback_reason"),
                              "at": created_at}
            if counting:
                consecutive += 1
        elif status == "ok" or status is None:
            counting = False
        # rule_only / rule_by_choice는 연속 실패를 끊지도 늘리지도 않는다
    return {"consecutive_failures": consecutive, "last_ok_at": last_ok_at, "last_error": last_error,
            "degraded": consecutive >= DEGRADED_AFTER}


def get_engine(conn: sqlite3.Connection, config: dict | None) -> dict:
    """GET /coach/engine 페이로드(design §7.2)."""
    selected = ((config or {}).get("ai") or {}).get("provider", "rule")
    consent = get_consent(conn)
    if selected not in LLM_PROVIDERS:
        mode = "rule_by_choice"
    elif not any(api_key_for(p, config) for p in LLM_PROVIDERS):
        mode = "rule_only"
    else:
        mode = "llm"
    chain, _ = build_chain(selected, config, consent, True)
    return {
        "mode": mode,
        "selected": {"provider": selected, "model": model_for(selected, config) if selected in LLM_PROVIDERS else None},
        "chain": [{"provider": p, "model": model_for(p, config)} for p in chain],
        "health": health_summary(conn),
        "consent": consent,
        "scope": scope_catalog(),
    }
