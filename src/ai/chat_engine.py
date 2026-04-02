"""AI 채팅 엔진 — 교체 가능 구조.

config.json의 ai.provider 설정에 따라 다른 AI API 호출.
지원: 'rule' (규칙 기반 fallback), 'claude', 'openai', 'genspark'.

모듈 분리:
  - chat_engine_providers.py: 외부 API provider 호출 (Claude/OpenAI/Gemini/Groq/Genspark)
  - chat_engine_rules.py:    규칙 기반 fallback 응답 (키워드 매칭)
  - chat_engine.py (이 파일): 코어 chat 함수 + 시스템 프롬프트 + re-export
"""
from __future__ import annotations

import logging
import sqlite3

from .chat_engine_rules import rule_based_response

from .chat_engine_providers import (
    RateLimitError,  # noqa: F401 (re-export)
    call_claude,
    call_gemini,
    call_groq,
    call_openai,
    call_with_tools,  
)

log = logging.getLogger(__name__)

# ── 하위 호환 private alias (ai_message.py 등에서 직접 참조) ──────────────
_call_claude = call_claude
_call_openai = call_openai
_call_gemini = call_gemini
_call_groq = call_groq


def get_ai_provider(config: dict | None = None) -> str:
    """설정에서 AI 제공자 이름 반환."""
    if not config:
        return "rule"
    return config.get("ai", {}).get("provider", "rule")


def chat(
    conn: sqlite3.Connection,
    user_message: str,
    config: dict | None = None,
    chip_id: str | None = None,
) -> str:
    """사용자 메시지에 대한 AI 응답 생성 — provider chain fallback 지원.

    Args:
        conn: DB 연결 (컨텍스트 빌드용).
        user_message: 사용자 입력 텍스트.
        config: 설정 dict.
        chip_id: 추천 칩 ID (칩 클릭 시).

    Returns:
        AI 응답 텍스트 (마크다운).
    """
    provider = get_ai_provider(config)

    # 최근 대화 이력 (맥락 유지)
    chat_history = _load_recent_chat(conn, limit=6)

    # 프롬프트 빌드
    if chip_id:
        from .briefing import build_chip_prompt
        prompt = build_chip_prompt(conn, chip_id)
    else:
        from .chat_context import build_chat_context
        ctx_text = build_chat_context(conn, user_message, chat_history, provider=provider)
        prompt = _build_system_prompt(ctx_text, user_message, chat_history)

    # provider chain: 선택 → gemini → groq → rule
    chain = _build_chat_provider_chain(provider, config)
    for prov in chain:
        try:
            if not chip_id:
                result = call_with_tools(conn, prompt, config, prov)
                if result:
                    return result, prov
                continue
            result = _call_provider(prov, prompt, config)
            if result:
                return result, prov
        except RateLimitError:
            log.warning("%s 429 → 다음 provider로 전환", prov)
            continue
        except Exception:
            log.warning("provider '%s' 실패, 다음으로", prov, exc_info=True)
            continue

    return rule_based_response(conn, user_message, chip_id), "rule"


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


def _load_recent_chat(conn: sqlite3.Connection, limit: int = 3) -> list[dict]:
    """최근 채팅 이력 로드 (프롬프트 컨텍스트용)."""
    try:
        rows = conn.execute(
            "SELECT role, content FROM chat_messages ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [{"role": r[0], "content": r[1]} for r in reversed(rows)]
    except Exception:
        return []
