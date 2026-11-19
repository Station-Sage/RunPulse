"""AI 채팅 엔진 — 교체 가능 구조.

config.json의 ai.provider 설정에 따라 다른 AI API 호출.
지원: 'rule' (규칙 기반 fallback), 'claude', 'openai', 'genspark'.

모듈 분리:
  - chat_engine_providers.py: 외부 API provider 호출 (Claude/OpenAI/Gemini/Groq/Genspark)
  - chat_engine_rules.py:    규칙 기반 fallback 응답 (chip_id 핸들러 디스패치)
  - chat_engine.py (이 파일): 코어 chat 함수 + 시스템 프롬프트 + re-export
"""
from __future__ import annotations

import logging
import re
import sqlite3
from datetime import date

from .chat_engine_result import (
    ChatResult, build_chain, engine_for_ok, engine_for_rule, run_chain,
)
from . import provider_claude_queue as pcq
from .provider_common import CLAUDE_QUEUE
from .chat_engine_rules import rule_based_response

from .chat_engine_providers import (
    RateLimitError,  # noqa: F401 (re-export)
    call_claude,
    call_gemini,
    call_groq,
    call_openai,
)

log = logging.getLogger(__name__)

def get_ai_provider(config: dict | None = None) -> str:
    """설정에서 AI 제공자 이름 반환."""
    if not config:
        return "rule"
    return config.get("ai", {}).get("provider", "rule")


_TRAILING_RECO = re.compile(r"\n*\[추천:[^\]]*\]\s*$")


def _with_activity_context(conn: sqlite3.Connection, thread_id: int | None, ctx_text: str) -> str:
    """활동 스레드(context_kind='activity')면 대상 활동 한 줄 요약을 컨텍스트 앞에 붙인다."""
    if thread_id is None:
        return ctx_text
    row = conn.execute("SELECT context_kind, context_ref FROM chat_threads WHERE id = ?",
                       (thread_id,)).fetchone()
    if not row or row[0] != "activity" or not str(row[1] or "").isdigit():
        return ctx_text
    from src.services.coach_activity_context import activity_prompt_summary
    summary = activity_prompt_summary(conn, int(row[1]))
    return f"{summary}\n\n{ctx_text}" if summary else ctx_text


def chat_result(
    conn: sqlite3.Connection,
    user_message: str,
    config: dict | None = None,
    chip_id: str | None = None,
    thread_id: int | None = None,
    consent: dict | None = None,
    require_consent: bool = False,
    on_event=None,
    cancelled=None,
    retire: str | None = None,
) -> ChatResult:
    """응답 + 엔진 상태(design §4.1). 동의된 provider만 호출하고, 실패하면 규칙 답변으로 끝낸다.

    consent: coach_consent 행 dict(provider/exclude_notes/tools_enabled/fallback_enabled).
    require_consent=True(Coach v2)면 동의가 없을 때 외부 호출을 하지 않는다.
    on_event("stage", payload)·cancelled()는 비동기 답변 상태 기계(design §6.2)용 훅이다(delta·done은 호출자가 결과로 만든다).
    """
    provider = get_ai_provider(config)
    consent_on = require_consent
    exclude_notes = bool(consent and consent.get("exclude_notes")) if consent_on else False
    tools_on = bool(consent.get("tools_enabled")) if consent_on and consent else True
    cq_wanted = provider == CLAUDE_QUEUE or CLAUDE_QUEUE in (((config or {}).get("ai") or {}).get("fallback_order") or [])
    cq_ok = cq_wanted and pcq.available(conn, config)
    chain, empty_reason = build_chain(provider, config, consent, consent_on, cq_available=cq_ok)

    chat_history = _load_recent_chat(conn, limit=6, thread_id=thread_id)
    sent_scope: list | None = None
    text: str | None = None
    used: str | None = None
    attempts: list = []
    cq: dict | None = None
    if chain:
        from .suggestions import CHIP_REGISTRY
        prompt_is_free = not (chip_id and chip_id in CHIP_REGISTRY)
        if not prompt_is_free:
            from .briefing import build_chip_prompt
            prompt = build_chip_prompt(conn, chip_id)
        else:
            from .chat_context import build_chat_context_scoped
            ctx_text, sent_scope = build_chat_context_scoped(
                conn, user_message, chat_history, provider=provider, exclude_notes=exclude_notes)
            ctx_text = _with_activity_context(conn, thread_id, ctx_text)
            prompt = _build_system_prompt(ctx_text, user_message, chat_history)
            if CLAUDE_QUEUE in chain:
                from .coach_cq_context import build_cq
                cq, cq_prompt = build_cq(conn, system_prompt=_SYSTEM_PROMPT, thread_id=thread_id, today_ctx=ctx_text,
                                         user_message=user_message, history=chat_history, retire=retire)
                prompt = (cq_prompt, prompt)
        text, used, attempts = run_chain(conn, prompt, config, chain, tools=tools_on,
                                         on_event=on_event, cancelled=cancelled, cq=cq)

    as_of = date.today().isoformat()
    if text and used:
        text = _TRAILING_RECO.sub("", text).rstrip() or text
        return ChatResult(text, engine_for_ok(used, attempts), as_of=as_of, sent_scope=sent_scope,
                          followups=llm_followups(conn, user_message, chip_id))
    if on_event is not None:
        on_event("stage", {"key": "rule", "label": "기본 답변 준비 중", "tool": None})
    answer = rule_based_response(conn, user_message, chip_id)
    return ChatResult(answer.text, engine_for_rule(provider, config, empty_reason, attempts),
                      evidence=answer.evidence, followups=list(answer.followups), as_of=as_of)


def llm_followups(conn: sqlite3.Connection, user_message: str, chip_id: str | None) -> list[str]:
    """LLM 답변에도 후속 칩을 붙인다 — 답할 수 있는 칩 중 질문과 가까운 순, 방금 누른 칩은 제외."""
    from .coach_rule_handlers import answerable_chips
    from .coach_rule_intent import rank_followups
    try:
        chips, _ = rank_followups(user_message, [c for c in answerable_chips(conn) if c != chip_id])
    except sqlite3.Error:
        return []
    return chips


def chat(
    conn: sqlite3.Connection,
    user_message: str,
    config: dict | None = None,
    chip_id: str | None = None,
    thread_id: int | None = None,
) -> tuple[str, str]:
    """v1 /ai-coach 호환 래퍼 — (응답 텍스트, 응답한 provider 이름 또는 "rule").

    thread_id를 주면 그 스레드의 이력만, None이면 기존처럼 전체 최근 메시지를 컨텍스트로 쓴다.
    """
    result = chat_result(conn, user_message, config, chip_id, thread_id)
    return result.text, result.engine.provider


def _build_chat_provider_chain(selected: str, config: dict | None) -> list[str]:
    """채팅용 provider 시도 순서."""
    ai_cfg = (config or {}).get("ai", {})
    chain = []
    _PROVIDERS = {"gemini", "groq", "claude", "openai"}
    if selected in _PROVIDERS:
        chain.append(selected)
    if "gemini" not in chain and ai_cfg.get("gemini_api_key"):
        chain.append("gemini")
    if "groq" not in chain and ai_cfg.get("groq_api_key"):
        chain.append("groq")
    return chain


def _call_provider(provider: str, prompt: str, config: dict | None) -> str | None:
    """단일 provider 호출. 성공 시 텍스트, 실패/429 시 None."""
    _dispatch = {
        "gemini": call_gemini, "groq": call_groq,
        "claude": call_claude, "openai": call_openai,
    }
    fn = _dispatch.get(provider)
    if not fn:
        return None
    try:
        result = fn(prompt, config)
        if result and "설정되지 않았습니다" not in result and "실패" not in result:
            return result
        return None
    except RateLimitError:
        log.warning("%s 429 rate limit → 다음 provider로 전환", provider)
        return None
    except Exception as exc:
        log.warning("provider '%s' 호출 실패: %s", provider, exc)
        return None


# ── 시스템 프롬프트 ──────────────────────────────────────────────────────

_SYSTEM_PROMPT = """당신은 RunPulse AI 러닝 코치입니다. 반드시 한국어로만 답변하세요.

## 핵심 원칙
- 아래 제공된 데이터만 사용. 데이터에 없는 수치를 만들어내지 마세요.
- 거리는 소수점 2자리 (예: 21.05km), 페이스/시간은 초 단위 (예: 5:30/km).
- 이전 대화 맥락을 반드시 이어서 답변하세요.

## 훈련 조언 원칙
- 대회 임박(D-14 이내): 테이퍼링 추천 (볼륨 감량, 강도 유지, 고강도 세션 축소)
- 대회 임박(D-7 이내): 경량 조깅/완전 휴식 추천
- CIRS < 30 + ACWR 0.8~1.3: 정상 훈련 가능. 이지런만 추천하지 마세요.
- 사용자가 "더 강하게", "스피드", "템포" 등 고강도를 원하면 데이터가 허용하는 범위에서 수용하세요.
- 훈련 추천 시 반드시 구체적으로: "내일 6km 템포런 (5:10/km 목표)" 형태.

## 데이터 해석
- CIRS < 25: 부상 위험 낮음, 고강도 가능
- CIRS 25~50: 주의, 중강도 권장
- CIRS > 75: 휴식 필수
- ACWR 0.8~1.3: 안전 범위
- TSB > 0: 신선, TSB < -20: 피로 축적
- 마지막 러닝이 7일 이상 전(휴식기)이면 TSB 높음을 곧바로 "컨디션 좋음"으로 읽지 말고, 지표와 상황이 엇갈린다고 먼저 짚은 뒤 복귀 첫 세션은 보수적으로(이지 위주) 제안하세요.
- HRV 28일 평균은 휴식기에 낮아질 수 있으니 장기(90일 이상) 기준선과 함께 비교하세요.
- 도구 결과가 비었으면 이유(기간·이름·데이터 없음)를 짧게 설명하고, 계획·체크인이 비어 있으면 그 점을 사용자에게 물어보세요.

## 훈련 계획 추천 형식
사용자가 훈련 스케줄/계획을 요청하면 반드시 아래 형식으로 답변:

**[날짜] [훈련 유형] [총 거리]km**
- 워밍업: [거리]km @ [페이스]/km
- 메인: [거리]km × [세트]회 @ [페이스]/km (회복 조깅 [거리]km @ [페이스]/km)
- 쿨다운: [거리]km @ [페이스]/km

예시:
**3/29(토) 템포런 10km**
- 워밍업: 2km @ 6:00/km
- 메인: 6km @ 5:10/km
- 쿨다운: 2km @ 6:30/km

**3/30(일) 인터벌 8km**
- 워밍업: 2km @ 6:00/km
- 메인: 1km × 4회 @ 4:30/km (회복 조깅 400m @ 6:30/km)
- 쿨다운: 1.6km @ 6:30/km

페이스는 Daniels VDOT 기반 E/M/T/I pace를 사용하세요.

## 응답 형식
1. 3~7문장 (훈련 계획 요청 시 필요한 만큼 길게).
2. 질문에 직접 답변부터.
3. 응답 마지막에 추천 질문 3개:
   [추천: 질문1 | 질문2 | 질문3]
"""


def _build_system_prompt(context: str, user_message: str,
                         chat_history: list[dict] | None = None) -> str:
    """시스템 프롬프트 + 컨텍스트 + 대화 이력 + 질문 조합."""
    parts = [_SYSTEM_PROMPT, "\n", context]

    if chat_history:
        parts.append("\n\n## 이전 대화")
        for msg in chat_history:
            role = "사용자" if msg.get("role") == "user" else "코치"
            parts.append(f"\n{role}: {msg.get('content', '')[:200]}")

    parts.append(f"\n\n## 사용자 질문\n{user_message}")
    return "".join(parts)


def _load_recent_chat(
    conn: sqlite3.Connection, limit: int = 3, thread_id: int | None = None,
) -> list[dict]:
    """최근 채팅 이력 로드 (프롬프트 컨텍스트용).

    thread_id가 주어지면 그 스레드로만 필터링한다(Phase 7 Coach). None이면 기존
    v1 동작대로 전체 최근 메시지를 사용한다.
    """
    try:
        if thread_id is not None:
            rows = conn.execute(
                "SELECT role, content FROM chat_messages WHERE thread_id = ? "
                "ORDER BY id DESC LIMIT ?",
                (thread_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT role, content FROM chat_messages ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [{"role": r[0], "content": r[1]} for r in reversed(rows)]
    except Exception:
        return []
