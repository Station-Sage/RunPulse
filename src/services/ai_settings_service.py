"""AI 설정 페이지 서비스 — provider·키 상태·전송 범위·7일 사용량·연결 테스트 (F-DATA-12, ADR-030).

키 값은 어떤 응답에도 싣지 않는다(상태와 끝 4자리 마스크만). 전송 범위는 chat_context_scope.scope_catalog() 기준이고
사용자가 끌 수 있는 항목은 체크인 메모(exclude_notes)뿐이다.
"""
from __future__ import annotations

import sqlite3

from src.ai.provider_common import LLM_PROVIDERS, ProviderError, api_key_for, model_for
from src.services import coach_consent, coach_engine_health
from src.utils.config import save_config

PROVIDER_CHOICES = ("rule", *LLM_PROVIDERS)
_PING_PROMPT = "ping. 한 단어로 답하세요."


def mask_key(key: str) -> str:
    return "" if not key else "••••" + key[-4:] if len(key) > 8 else "••••"


def key_state(provider: str, config: dict, health: dict) -> str:
    """set | missing | invalid (마지막 오류가 401이고 이후 성공이 없으면 invalid)."""
    if not api_key_for(provider, config):
        return "missing"
    err = health.get("last_error") or {}
    if err.get("provider") == provider and err.get("reason") == "http_401" and not health.get("last_ok_at"):
        return "invalid"
    return "set"


def usage_7d(conn: sqlite3.Connection) -> dict:
    rows = conn.execute(
        "SELECT engine_json FROM chat_messages WHERE role='assistant' AND engine_json IS NOT NULL"
        " AND created_at >= datetime('now', '-7 days')").fetchall()
    by_provider: dict[str, int] = {}
    total = fallback = rule = tool_calls = 0
    for (raw,) in rows:
        eng = coach_engine_health.parse_engine(raw) or {}
        status = eng.get("status")
        total += 1
        tool_calls += int(eng.get("tool_calls") or 0)
        if status == "ok":
            by_provider[eng.get("provider") or "?"] = by_provider.get(eng.get("provider") or "?", 0) + 1
        elif status == "fallback":
            fallback += 1
        elif status in ("rule_only", "rule_by_choice"):
            rule += 1
    return {"messages": total, "by_provider": by_provider, "fallback": fallback, "rule": rule, "tool_calls": tool_calls}


def build_view(conn: sqlite3.Connection, config: dict) -> dict:
    engine = coach_engine_health.get_engine(conn, config)
    health = engine["health"]
    consent = engine["consent"] or {}
    providers = [{"provider": p, "model": model_for(p, config), "key_state": key_state(p, config, health),
                  "key_mask": mask_key(api_key_for(p, config))} for p in LLM_PROVIDERS]
    err = health.get("last_error")
    notes_off = bool(consent.get("exclude_notes"))
    scope = [{**s, "enabled": not (s.get("optional") and notes_off)} for s in engine["scope"]]
    return {
        "provider": engine["selected"]["provider"], "providers": providers, "mode": engine["mode"],
        "fallback_enabled": consent.get("fallback_enabled", True), "exclude_notes": notes_off,
        "consented": bool(consent.get("accepted_at")) and consent.get("provider") == engine["selected"]["provider"],
        "scope": scope, "usage_7d": usage_7d(conn),
        "chain": engine["chain"], "health": health,
        "last_error_label": coach_engine_health.reason_label(err.get("reason")) if err else None,
    }


def validate_patch(body: dict) -> tuple[dict, str | None]:
    out: dict = {}
    if "provider" in body:
        if body["provider"] not in PROVIDER_CHOICES:
            return {}, f"provider는 {', '.join(PROVIDER_CHOICES)} 중 하나예요"
        out["provider"] = body["provider"]
    if "keys" in body:
        keys = body["keys"]
        if not isinstance(keys, dict) or set(keys) - set(LLM_PROVIDERS):
            return {}, "keys는 provider별 문자열이에요"
        clean = {}
        for p, v in keys.items():
            if not isinstance(v, str):
                return {}, "keys는 provider별 문자열이에요"
            if v.strip():
                clean[p] = v.strip()
        out["keys"] = clean
    for k in ("exclude_notes", "fallback_enabled"):
        if k in body:
            if not isinstance(body[k], bool):
                return {}, f"{k}는 true/false예요"
            out[k] = body[k]
    return (out, None) if out else ({}, "바꿀 항목이 없어요")


def apply_patch(conn: sqlite3.Connection, config: dict, user_id: str, changes: dict) -> None:
    ai = config.setdefault("ai", {})
    if "provider" in changes:
        ai["provider"] = changes["provider"]
    for p, v in changes.get("keys", {}).items():
        ai[f"{p}_api_key"] = v
    save_config(config, user_id=user_id)
    provider = ai.get("provider", "rule")
    current = coach_consent.get_consent(conn) or {}
    if provider in LLM_PROVIDERS and ({"provider", "exclude_notes", "fallback_enabled"} & set(changes) or not current):
        coach_consent.save_consent(
            conn, provider,
            exclude_notes=changes.get("exclude_notes", current.get("exclude_notes", False)),
            tools_enabled=current.get("tools_enabled", True),
            fallback_enabled=changes.get("fallback_enabled", current.get("fallback_enabled", True)))
    elif current and current.get("provider") in LLM_PROVIDERS and {"exclude_notes", "fallback_enabled"} & set(changes):
        coach_consent.save_consent(
            conn, current["provider"],
            exclude_notes=changes.get("exclude_notes", current["exclude_notes"]),
            tools_enabled=current["tools_enabled"],
            fallback_enabled=changes.get("fallback_enabled", current["fallback_enabled"]))


def test_connection(provider: str, config: dict) -> dict:
    """아주 짧은 프롬프트 1회 호출. {ok, reason, label, http_status}."""
    from src.ai.chat_engine_providers import complete

    if not api_key_for(provider, config):
        return {"ok": False, "reason": "no_key", "label": coach_engine_health.reason_label("no_key"), "http_status": None}
    try:
        complete(provider, _PING_PROMPT, config)
    except ProviderError as exc:
        return {"ok": False, "reason": exc.reason, "label": coach_engine_health.reason_label(exc.reason),
                "http_status": exc.http_status}
    return {"ok": True, "reason": None, "label": "연결됐어요", "http_status": None}
