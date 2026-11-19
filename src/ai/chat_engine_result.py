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
from .llm_budget import BUDGET_REASONS, QUOTA_REASONS, resets_at
from .provider_common import (
    CLAUDE_QUEUE, CQ_COACH_DEADLINE, LLM_PROVIDERS, TOTAL_BUDGET, ProviderError, api_key_for, model_for,
)

log = logging.getLogger(__name__)

FALLBACK_ORDER = ("gemini", "groq")
MODEL_COACH_LABEL = "claude-sonnet"


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
    resets_at: str | None = None   # quota_* 규칙 대체 시 다음 00:00 KST (multiuser-sync §4.3)


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


MAX_FALLBACKS = 2


def fallback_providers(selected: str, config: dict | None, keyed: list[str], cq_available: bool) -> list[str]:
    """2·3순위 폴백(최대 2개). ai.fallback_order 가 없으면 기본 FALLBACK_ORDER. 키 없는 provider·큐 불가는 건너뛴다."""
    raw = ((config or {}).get("ai") or {}).get("fallback_order")
    order = FALLBACK_ORDER if raw is None else raw
    out: list[str] = []
    for p in order:
        usable = cq_available if p == CLAUDE_QUEUE else p in keyed
        if p != selected and usable and p not in out:
            out.append(p)
    return out[:MAX_FALLBACKS]


def build_chain(selected: str, config: dict | None, consent: dict | None,
                require_consent: bool, *, cq_available: bool = False) -> tuple[list[str], str | None]:
    """(시도할 provider 목록, 체인이 비었을 때 사유 no_key/no_consent/None).

    선택 → 2순위 → 3순위(ai.fallback_order, 기본 gemini·groq) → 규칙. selected=claude_queue 는 키 없이 큐 가용 여부(cq_available)로 선두를 정한다.
    require_consent=False(v1 /ai-coach)는 동의 없이 같은 순서. 동의 모드에서는 동의의 fallback_enabled 가 꺼져 있으면 폴백 없음.
    """
    keyed = [p for p in LLM_PROVIDERS if api_key_for(p, config)]
    fb_on = not require_consent or bool((consent or {}).get("fallback_enabled"))
    fallbacks = fallback_providers(selected, config, keyed, cq_available) if fb_on else []
    if selected == CLAUDE_QUEUE:
        if require_consent and (not consent or consent.get("provider") != CLAUDE_QUEUE):
            return [], "no_consent"
        chain = ([CLAUDE_QUEUE] if cq_available else []) + fallbacks
        return chain, (None if chain else "no_key")
    if selected not in LLM_PROVIDERS:
        return [], None
    if not keyed:
        return [], "no_key"
    if not require_consent:
        chain = ([selected] if selected in keyed else []) + fallbacks
        return chain, ("no_key" if not chain else None)
    if not consent or consent.get("provider") != selected:
        return [], "no_consent"
    if selected not in keyed:
        return [], "no_key"
    return [selected] + fallbacks, None


def run_chain(conn: sqlite3.Connection, prompt: str, config: dict | None, chain: list[str],
              *, tools: bool, on_event=None,
              cancelled=None, cq: dict | None = None) -> tuple[str | None, str | None, list[Attempt]]:
    """체인을 순서대로 호출. prompt 가 (cq용, 폴백용) 튜플이면 provider 별로 골라 쓴다. (텍스트, 응답한 provider, attempts). 전부 실패하면 (None, None, attempts).

    on_event("stage", {...})를 provider 호출 전·조회 도구마다 보낸다. cancelled()가 True면 다음 호출 전에 멈춘다.
    """
    deadline = time.monotonic() + TOTAL_BUDGET
    attempts: list[Attempt] = []
    for prov in chain:
        if cancelled is not None and cancelled():
            break
        if prov == CLAUDE_QUEUE:
            cq = {**(cq or {}), "deadline_sec": (cq or {}).get("deadline_sec") or CQ_COACH_DEADLINE,
                  "should_cancel": cancelled}
        elif attempts and attempts[-1].provider == CLAUDE_QUEUE:
            deadline = time.monotonic() + TOTAL_BUDGET   # 큐 대기가 폴백 예산을 갉아먹지 않게 재시작
        stats: dict = {}
        if on_event is not None:
            on_event("stage", {"key": "model", "label": "답변 작성 중", "tool": None, "provider": prov})
        started = time.monotonic()
        attempt = Attempt(provider=prov, ok=False,
                          model=(MODEL_COACH_LABEL if prov == CLAUDE_QUEUE else model_for(prov, config)))
        try:
            text = complete(prov, (prompt[0] if prov == CLAUDE_QUEUE else prompt[1]) if isinstance(prompt, tuple) else prompt, config, conn=conn, tools=tools, deadline=deadline, stats=stats, **({"cq": cq} if prov == CLAUDE_QUEUE else {}),
                            on_tool=(lambda name: on_event("stage", {
                                "key": "tool", "label": f"데이터 확인 중: {name}", "tool": name}))
                            if on_event is not None else None)
            attempt.ok = bool(text)
            if not text:
                attempt.reason = "parse_error"
        except ProviderError as exc:
            attempt.reason, attempt.http_status = exc.reason, exc.http_status
            log.warning("provider '%s' 실패(%s)", prov, exc.reason)
        except Exception:
            attempt.reason = "unexpected"   # C-14: 전송 오류가 아닌 예외를 '네트워크 오류'로 뭉뚱그리지 않는다
            log.warning("provider '%s' 예기치 못한 실패", prov, exc_info=True)
        attempt.latency_ms = int((time.monotonic() - started) * 1000)
        attempt.tool_calls = stats.get("tool_calls", 0)
        attempts.append(attempt)
        if attempt.ok:
            return text, prov, attempts
        if attempt.reason in BUDGET_REASONS or time.monotonic() >= deadline:
            break  # 예산 거부는 사용자·전역 단위라 다음 provider도 같은 결과
    return None, None, attempts


def engine_for_rule(selected: str, config: dict | None, empty_reason: str | None,
                    attempts: list[Attempt]) -> EngineInfo:
    """규칙 답변이 나간 경우의 EngineInfo — 선택(끔)/AI 미설정/미동의/전 provider 실패를 구분한다."""
    if attempts:
        reason = next((a.reason for a in attempts if a.reason in BUDGET_REASONS), attempts[0].reason)
        resets = resets_at() if reason in QUOTA_REASONS else None
        return EngineInfo("fallback", "rule", None, attempts, reason, resets_at=resets)
    if selected == "rule" or (selected not in LLM_PROVIDERS and selected != CLAUDE_QUEUE):
        return EngineInfo("rule_by_choice")
    return EngineInfo("rule_only", fallback_reason=empty_reason or "no_key")


def engine_for_ok(provider: str, attempts: list[Attempt]) -> EngineInfo:
    switched = attempts[0].reason if attempts[0].provider != provider else None
    return EngineInfo("ok", provider, attempts[-1].model, attempts, switched, sum(a.tool_calls for a in attempts))


__all__ = ["Attempt", "ChatResult", "EngineInfo", "build_chain", "run_chain", "engine_for_ok",
           "engine_for_rule"]
