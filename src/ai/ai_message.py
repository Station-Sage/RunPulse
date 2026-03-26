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
            if cache_key:
                if len(_cache) >= _CACHE_MAX:
                    _cache.clear()
                _cache[cache_key] = result
            return result

    return rule_based_fallback


def get_card_ai_message(
    card_key: str,
    conn: sqlite3.Connection,
    rule_based_fallback: str,
    config: dict | None = None,
    **extra_kwargs,
) -> str:
    """카드별 AI 메시지 생성 — 컨텍스트 빌더 + 프롬프트 템플릿 자동 사용.

    Args:
        card_key: prompt_config.py의 키 (예: 'dashboard_recommendation').
        conn: DB 연결 (컨텍스트 빌드용).
        rule_based_fallback: 규칙 기반 메시지.
        config: 설정 dict.
        **extra_kwargs: 추가 템플릿 변수.

    Returns:
        AI 응답 또는 규칙 기반 메시지.
    """
    if not config or config.get("ai", {}).get("provider", "rule") == "rule":
        return rule_based_fallback

    try:
        from .context_builders import (
            build_dashboard_context,
            build_training_context,
            build_report_context,
            build_race_context,
            build_wellness_context,
            build_activity_context,
            format_context_compact,
        )
        from .prompt_config import get_prompt
        from datetime import date

        today = date.today().isoformat()

        # 카드 키에서 탭 추출
        tab = card_key.split("_")[0]
        ctx = {}
        if tab == "dashboard":
            ctx = build_dashboard_context(conn, today)
        elif tab == "training":
            ctx = build_training_context(conn, today)
        elif tab == "report":
            start = extra_kwargs.get("start_date", today)
            end = extra_kwargs.get("end_date", today)
            ctx = build_report_context(conn, start, end)
        elif tab == "race":
            ctx = build_race_context(conn, today)
        elif tab == "wellness":
            ctx = build_wellness_context(conn, today)
        elif tab == "activity":
            aid = extra_kwargs.get("activity_id")
            if aid:
                ctx = build_activity_context(conn, aid)
        elif tab == "coach":
            ctx = build_dashboard_context(conn, today)  # 코치는 대시보드 컨텍스트 사용

        context_text = format_context_compact(ctx)
        system, prompt = get_prompt(
            card_key, config,
            context=context_text,
            **{k: v for k, v in extra_kwargs.items() if k not in ("start_date", "end_date", "activity_id")},
        )

        full_prompt = f"{system}\n\n{prompt}" if system else prompt
        return get_ai_message(full_prompt, rule_based_fallback, config, cache_key=card_key)

    except Exception as exc:
        log.warning("카드 AI 메시지 생성 실패 (%s): %s", card_key, exc)
        return rule_based_fallback


def get_tab_ai(
    tab: str,
    conn: sqlite3.Connection,
    config: dict | None = None,
    cache_key: str = "default",
    **extra_kwargs,
) -> dict | None:
    """탭별 1회 통합 AI 호출 — 캐시 우선, 검증 + 재시도.

    Args:
        tab: 탭 이름 ('dashboard', 'activity', 'report', ...).
        conn: DB 연결.
        config: 설정 dict.
        cache_key: 캐시 키 (활동 ID, 기간 등).
        **extra_kwargs: start_date, end_date, activity_id 등.

    Returns:
        AI 해석 dict 또는 None (AI 비활성/실패).
    """
    if not config or config.get("ai", {}).get("provider", "rule") == "rule":
        return None

    # 1. 캐시 확인
    try:
        from .ai_cache import get_cached, get_cache_age
        cached = get_cached(conn, tab, cache_key)
        if cached:
            age = get_cache_age(conn, tab, cache_key)
            if age:
                cached["_ai_cache_age"] = age
            return cached
    except Exception:
        pass

    # 2. 컨텍스트 빌드
    try:
        from .context_builders import (
            build_dashboard_context, build_training_context,
            build_report_context, build_race_context,
            build_wellness_context, build_activity_context,
            format_context_compact,
        )
        from .prompt_config import get_tab_prompt
        from datetime import date

        today = date.today().isoformat()
        if tab == "dashboard":
            ctx = build_dashboard_context(conn, today)
        elif tab == "training":
            ctx = build_training_context(conn, today)
        elif tab == "report":
            ctx = build_report_context(conn,
                                       extra_kwargs.get("start_date", today),
                                       extra_kwargs.get("end_date", today))
        elif tab == "race":
            ctx = build_race_context(conn, today)
        elif tab == "wellness":
            ctx = build_wellness_context(conn, today)
        elif tab == "activity":
            aid = extra_kwargs.get("activity_id")
            ctx = build_activity_context(conn, aid) if aid else {}
        else:
            ctx = {}

        context_text = format_context_compact(ctx)
        prompt = get_tab_prompt(tab, context=context_text, **extra_kwargs)
    except Exception as exc:
        log.warning("탭 AI 컨텍스트 빌드 실패 (%s): %s", tab, exc)
        return None

    # 3. API 호출 + 검증 + 재시도
    from .ai_validator import validate_response, parse_json_response

    providers = _build_provider_chain(
        config.get("ai", {}).get("provider", "rule"),
        config.get("ai", {}),
    )

    for attempt in range(2):
        temp = 0.3 if attempt == 0 else 0.1
        for prov in providers:
            result_text = _try_provider_with_temp(prov, prompt, config, temp)
            if not result_text:
                continue

            parsed = parse_json_response(result_text)
            if not parsed:
                log.info("탭 AI JSON 파싱 실패 (%s, attempt=%d)", tab, attempt)
                continue

            ok, reason = validate_response(tab, parsed, ctx)
            if ok:
                # 캐시 저장
                try:
                    from .ai_cache import set_cached
                    set_cached(conn, tab, cache_key, parsed)
                except Exception:
                    pass
                return parsed
            else:
                log.info("탭 AI 검증 실패 (%s): %s", tab, reason)
                # 재시도 프롬프트에 실패 이유 추가
                prompt += f"\n\n[이전 응답이 부적절: {reason}. 다시 답변하세요.]"
                break  # 다음 attempt로

    return None


def _try_provider_with_temp(provider: str, prompt: str, config: dict,
                            temperature: float) -> str | None:
    """temperature 지정하여 provider 호출. 429 시 None → 다음 provider로."""
    try:
        from src.ai.chat_engine import (
            RateLimitError, _call_gemini, _call_groq, _call_claude, _call_openai,
        )
        import copy
        cfg = copy.deepcopy(config)
        cfg.setdefault("ai", {})["_temperature"] = temperature

        _dispatch = {
            "gemini": _call_gemini, "groq": _call_groq,
            "claude": _call_claude, "openai": _call_openai,
        }
        fn = _dispatch.get(provider)
        if not fn:
            return None
        result = fn(prompt, cfg)
        if result and "설정되지 않았습니다" not in result and "실패" not in result:
            return result
        return None
    except RateLimitError:
        log.warning("%s 429 rate limit → 다음 provider로 전환", provider)
        return None
    except Exception as exc:
        log.warning("AI provider '%s' 실패: %s", provider, exc)
        return None


def _build_provider_chain(selected: str, ai_cfg: dict) -> list[str]:
    """provider 시도 순서: 선택 → gemini → groq."""
    chain = []
    if selected and selected not in ("rule", "genspark", "genspark_auto"):
        chain.append(selected)
    if "gemini" not in chain and ai_cfg.get("gemini_api_key"):
        chain.append("gemini")
    if "groq" not in chain and ai_cfg.get("groq_api_key"):
        chain.append("groq")
    return chain


def _try_provider(provider: str, prompt: str, config: dict) -> str | None:
    """단일 provider 호출. 성공 시 텍스트, 429/실패 시 None."""
    try:
        from src.ai.chat_engine import (
            RateLimitError, _call_claude, _call_gemini, _call_groq, _call_openai,
        )
        _dispatch = {
            "gemini": _call_gemini, "groq": _call_groq,
            "claude": _call_claude, "openai": _call_openai,
        }
        fn = _dispatch.get(provider)
        if not fn:
            return None
        result = fn(prompt, config)
        if result and "설정되지 않았습니다" not in result and "실패" not in result:
            return result
        return None
    except RateLimitError:
        log.warning("%s 429 rate limit → 다음 provider로 전환", provider)
        return None
    except Exception as exc:
        log.warning("AI provider '%s' 실패: %s", provider, exc)
        return None
