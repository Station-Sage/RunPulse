"""채팅 엔진 결과 모델 + provider 체인 실행 (30-coach-chat design §4.1·§4.3·§6.2).

ChatResult = {text, engine{status, provider, model, attempts[], fallback_reason}, evidence, followups, as_of, sent_scope}.
체인은 사용자가 동의한 provider만 담고(동의 전 외부 호출 0회), 전체 예산 45초를 넘기면 규칙 답변으로 끝낸다.
"""
from __future__ import annotations

import logging
import sqlite3
import time
from dataclasses import asdict, dataclass, field

from .chat_engine_providers import complete
from .provider_common import (
    LLM_PROVIDERS, TOTAL_BUDGET, ProviderError, api_key_for, model_for,
)

log = logging.getLogger(__name__)

FALLBACK_ORDER = ("gemini", "groq")


@dataclass
class Attempt:
    provider: str
    model: str
    ok: bool
    reason: str | None = None
    http_status: int | None = None
    latency_ms: int = 0
    tool_calls: int = 0


@dataclass
class EngineInfo:
    status: str  # ok | fallback | rule_only | rule_by_choice
    provider: str = "rule"
    model: str | None = None
    attempts: list[Attempt] = field(default_factory=list)
    fallback_reason: str | None = None
    tool_calls: int = 0


@dataclass
class ChatResult:
    text: str
    engine: EngineInfo
    evidence: list = field(default_factory=list)
    followups: list = field(default_factory=list)
    as_of: str | None = None
    sent_scope: list | None = None

    def engine_dict(self) -> dict:
        return asdict(self.engine)


def build_chain(selected: str, config: dict | None, consent: dict | None,
                require_consent: bool) -> tuple[list[str], str | None]:
    """(시도할 provider 목록, 체인이 비었을 때 사유 no_key/no_consent/None).

    require_consent=False(v1 /ai-coach)는 기존 동작 — 선택 provider → 키가 있는 gemini/groq.
    """
    if selected not in LLM_PROVIDERS:
        return [], None
    keyed = [p for p in LLM_PROVIDERS if api_key_for(p, config)]
    if not keyed:
        return [], "no_key"
    if not require_consent:
        chain = [selected] if selected in keyed else []
        chain += [p for p in FALLBACK_ORDER if p != selected and p in keyed]
        return chain, ("no_key" if not chain else None)
    if not consent or consent.get("provider") != selected:
        return [], "no_consent"
    if selected not in keyed:
        return [], "no_key"
    chain = [selected]
    if consent.get("fallback_enabled"):
        chain += [p for p in FALLBACK_ORDER if p != selected and p in keyed]
    return chain, None


def run_chain(conn: sqlite3.Connection, prompt: str, config: dict | None, chain: list[str],
              *, tools: bool) -> tuple[str | None, str | None, list[Attempt]]:
    """체인을 순서대로 호출. (텍스트, 응답한 provider, attempts). 전부 실패하면 (None, None, attempts)."""
    deadline = time.monotonic() + TOTAL_BUDGET
    attempts: list[Attempt] = []
    for prov in chain:
        stats: dict = {}
        started = time.monotonic()
        attempt = Attempt(provider=prov, model=model_for(prov, config), ok=False)
        try:
            text = complete(prov, prompt, config, conn=conn, tools=tools, deadline=deadline, stats=stats)
            attempt.ok = bool(text)
            if not text:
                attempt.reason = "parse_error"
        except ProviderError as exc:
            attempt.reason, attempt.http_status = exc.reason, exc.http_status
            log.warning("provider '%s' 실패(%s)", prov, exc.reason)
        except Exception:
            attempt.reason = "network"
            log.warning("provider '%s' 예기치 못한 실패", prov, exc_info=True)
        attempt.latency_ms = int((time.monotonic() - started) * 1000)
        attempt.tool_calls = stats.get("tool_calls", 0)
        attempts.append(attempt)
        if attempt.ok:
            return text, prov, attempts
        if time.monotonic() >= deadline:
            break
    return None, None, attempts


def engine_for_rule(selected: str, config: dict | None, empty_reason: str | None,
                    attempts: list[Attempt]) -> EngineInfo:
    """규칙 답변이 나간 경우의 EngineInfo — 선택(끔)/AI 미설정/미동의/전 provider 실패를 구분한다."""
    if attempts:
        return EngineInfo("fallback", "rule", None, attempts, attempts[0].reason)
    if selected == "rule" or selected not in LLM_PROVIDERS:
        return EngineInfo("rule_by_choice")
    return EngineInfo("rule_only", fallback_reason=empty_reason or "no_key")


def engine_for_ok(provider: str, attempts: list[Attempt]) -> EngineInfo:
    switched = attempts[0].reason if attempts[0].provider != provider else None
    return EngineInfo("ok", provider, attempts[-1].model, attempts, switched, sum(a.tool_calls for a in attempts))


__all__ = ["Attempt", "ChatResult", "EngineInfo", "build_chain", "run_chain", "engine_for_ok",
           "engine_for_rule"]
