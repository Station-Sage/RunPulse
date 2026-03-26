"""AI 우선 메시지 생성기 — API 있으면 AI, 없으면 규칙 기반.

모든 UI 메시지를 이 모듈을 통해 생성합니다.
provider 우선순위: 사용자 선택 → gemini → groq → 규칙 기반.
"""
from __future__ import annotations

import logging
import sqlite3
from typing import Any

log = logging.getLogger(__name__)

# 캐시: 같은 세션에서 동일 프롬프트 재요청 방지
_cache: dict[str, str] = {}
_CACHE_MAX = 50


def get_ai_message(
    prompt: str,
    rule_based_fallback: str,
    config: dict | None = None,
    cache_key: str | None = None,
) -> str:
    """AI 우선 메시지 생성. 실패 시 규칙 기반 fallback.

    Args:
        prompt: AI에게 보낼 프롬프트.
        rule_based_fallback: AI 실패 시 표시할 규칙 기반 메시지.
        config: 설정 dict (ai 섹션).
        cache_key: 캐시 키 (같은 키면 재사용).

    Returns:
        AI 응답 또는 규칙 기반 메시지.
    """
    if not config:
        return rule_based_fallback

    # 캐시 확인
    if cache_key and cache_key in _cache:
        return _cache[cache_key]

    ai_cfg = config.get("ai", {})
    provider = ai_cfg.get("provider", "rule")

    # 규칙 기반이면 바로 반환
    if provider == "rule":
        return rule_based_fallback

    # provider 시도 순서
    providers_to_try = _build_provider_chain(provider, ai_cfg)

    for prov in providers_to_try:
        result = _try_provider(prov, prompt, config)
        if result:
            # 캐시 저장
            if cache_key:
                if len(_cache) >= _CACHE_MAX:
                    _cache.clear()
                _cache[cache_key] = result
            return result

    # 전부 실패 → 규칙 기반
    return rule_based_fallback


def get_metric_interpretation(
    metric_name: str,
    value: float,
    context: dict | None = None,
    config: dict | None = None,
) -> str:
    """메트릭 값에 대한 AI 해석. 규칙 기반 fallback 포함.

    Args:
        metric_name: 메트릭 이름 (UTRS, CIRS, ACWR 등).
        value: 현재 값.
        context: 추가 컨텍스트 (최근 추세, 이전 값 등).
        config: 설정 dict.

    Returns:
        해석 메시지.
    """
    rule_msg = _rule_based_interpretation(metric_name, value, context)

    if not config or config.get("ai", {}).get("provider", "rule") == "rule":
        return rule_msg

    prompt = _build_interpretation_prompt(metric_name, value, context)
    return get_ai_message(
        prompt=prompt,
        rule_based_fallback=rule_msg,
        config=config,
        cache_key=f"interp:{metric_name}:{value:.1f}",
    )


def _build_provider_chain(selected: str, ai_cfg: dict) -> list[str]:
    """provider 시도 순서 생성. 선택 → gemini → groq."""
    chain = []
    if selected and selected not in ("rule", "genspark"):
        chain.append(selected)
    # 무료 provider fallback
    if "gemini" not in chain and ai_cfg.get("gemini_api_key"):
        chain.append("gemini")
    if "groq" not in chain and ai_cfg.get("groq_api_key"):
        chain.append("groq")
    return chain


def _try_provider(provider: str, prompt: str, config: dict) -> str | None:
    """단일 provider 호출 시도. 성공 시 텍스트, 실패 시 None."""
    try:
        from src.ai.chat_engine import (
            _call_claude, _call_gemini, _call_groq, _call_openai,
        )
        _dispatch = {
            "gemini": _call_gemini,
            "groq": _call_groq,
            "claude": _call_claude,
            "openai": _call_openai,
        }
        fn = _dispatch.get(provider)
        if not fn:
            return None
        result = fn(prompt, config)
        # 에러 메시지인지 확인
        if result and "API 키가 설정되지 않았습니다" not in result and "실패" not in result:
            return result
        return None
    except Exception as exc:
        log.warning("AI provider '%s' 실패: %s", provider, exc)
        return None


def _build_interpretation_prompt(metric_name: str, value: float,
                                  context: dict | None = None) -> str:
    """메트릭 해석 프롬프트 생성."""
    from src.web.helpers import METRIC_DESCRIPTIONS
    desc = METRIC_DESCRIPTIONS.get(metric_name, "")

    ctx_parts = []
    if context:
        if context.get("prev_value") is not None:
            ctx_parts.append(f"이전 값: {context['prev_value']:.1f}")
        if context.get("trend"):
            ctx_parts.append(f"추세: {context['trend']}")
        if context.get("days_data"):
            ctx_parts.append(f"최근 {context['days_data']}일 데이터 기반")
    ctx_text = " | ".join(ctx_parts) if ctx_parts else ""

    return (
        f"당신은 러닝 코치입니다. 아래 메트릭을 한국어 1~2문장으로 해석해주세요.\n\n"
        f"메트릭: {metric_name}\n"
        f"현재 값: {value}\n"
        f"설명: {desc}\n"
        f"{f'컨텍스트: {ctx_text}' if ctx_text else ''}\n\n"
        f"러너에게 실질적인 조언을 포함해 짧게 답변하세요."
    )


def _rule_based_interpretation(metric_name: str, value: float,
                                context: dict | None = None) -> str:
    """규칙 기반 메트릭 해석."""
    _RULES: dict[str, list[tuple[float, str, str]]] = {
        # (threshold, operator, message) — threshold 이상이면 해당 메시지
        "UTRS": [
            (85, ">=", "컨디션 최고. 고강도 훈련 가능"),
            (70, ">=", "정상 훈련 가능"),
            (40, ">=", "볼륨 감소 권장"),
            (0, ">=", "완전 휴식 권장"),
        ],
        "CIRS": [
            (75, ">=", "부상 위험 높음. 훈련 중단"),
            (50, ">=", "주의 필요. 워밍업 충실히"),
            (25, ">=", "보통. 계속 모니터링"),
            (0, ">=", "안전. 정상 훈련"),
        ],
        "ACWR": [
            (1.5, ">=", "부상 위험. 볼륨 줄이세요"),
            (1.3, ">=", "주의 구간. 점진적 증가만"),
            (0.8, ">=", "적정 훈련량 (Sweet Spot)"),
            (0, ">=", "훈련 부족. 볼륨 늘리세요"),
        ],
        "RTTI": [
            (130, ">=", "과부하. 훈련량 감소 필요"),
            (100, ">=", "적정 한계. 현재 유지"),
            (70, ">=", "여유 있음. 강도 올려도 됨"),
            (0, ">=", "훈련 부족"),
        ],
        "DI": [
            (70, ">=", "내구성 우수. 장거리 준비 양호"),
            (40, ">=", "보통. 장거리 훈련 더 필요"),
            (0, ">=", "내구성 부족. 장거리 러닝 추가"),
        ],
        "REC": [
            (60, ">=", "효율 양호. 같은 노력으로 더 빠름"),
            (30, ">=", "보통. 지속적 개선 중"),
            (0, ">=", "효율 낮음. 폼/페이스 점검 필요"),
        ],
        "RRI": [
            (80, ">=", "레이스 준비 완료!"),
            (60, ">=", "보통. 추가 훈련 필요"),
            (0, ">=", "준비 부족. 목표 재검토 권장"),
        ],
        "TSB": [
            (10, ">=", "신선한 상태. 레이스 가능"),
            (-10, ">=", "적정 훈련 상태"),
            (-30, ">=", "피로 축적. 회복 필요"),
            (-100, ">=", "과훈련 위험"),
        ],
    }
    rules = _RULES.get(metric_name)
    if not rules:
        return f"{metric_name}: {value}"
    for threshold, op, msg in rules:
        if op == ">=" and value >= threshold:
            return msg
    return f"{metric_name}: {value}"
