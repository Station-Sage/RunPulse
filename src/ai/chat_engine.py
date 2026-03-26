"""AI 채팅 엔진 — 교체 가능 구조.

config.json의 ai.provider 설정에 따라 다른 AI API 호출.
지원: 'rule' (규칙 기반 fallback), 'claude', 'openai', 'genspark'.
"""
from __future__ import annotations

import json
import logging
import sqlite3
from typing import Any

log = logging.getLogger(__name__)


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
    """사용자 메시지에 대한 AI 응답 생성.

    Args:
        conn: DB 연결 (컨텍스트 빌드용).
        user_message: 사용자 입력 텍스트.
        config: 설정 dict.
        chip_id: 추천 칩 ID (칩 클릭 시).

    Returns:
        AI 응답 텍스트 (마크다운).
    """
    provider = get_ai_provider(config)

    # 프롬프트 빌드
    if chip_id:
        from .briefing import build_chip_prompt
        prompt = build_chip_prompt(conn, chip_id)
    else:
        from .ai_context import build_context, format_context_text
        ctx = build_context(conn)
        ctx_text = format_context_text(ctx)
        prompt = f"당신은 RunPulse AI 러닝 코치입니다. 아래 분석 데이터를 참고하여 답변하세요.\n\n{ctx_text}\n\n사용자 질문: {user_message}"

    # 제공자별 분기
    if provider == "claude":
        return _call_claude(prompt, config)
    elif provider == "openai":
        return _call_openai(prompt, config)
    elif provider == "genspark":
        return _call_genspark(prompt, config)
    else:
        return _rule_based_response(conn, user_message, chip_id)


def _rule_based_response(
    conn: sqlite3.Connection,
    user_message: str,
    chip_id: str | None = None,
) -> str:
    """규칙 기반 fallback 응답 (API 없을 때)."""
    from .ai_context import build_context, format_context_text

    ctx = build_context(conn)
    parts: list[str] = []

    # 칩별 특화 응답
    if chip_id == "today_deep":
        act = ctx.get("today_activity")
        if act:
            parts.append(f"**오늘 활동 분석**\n- 거리: {act.get('distance_km', '-')}km\n"
                         f"- 페이스: {act.get('avg_pace_sec_km', '-')}초/km\n"
                         f"- 심박: {act.get('avg_hr', '-')}bpm")
        else:
            parts.append("오늘은 아직 활동이 기록되지 않았습니다.")
    elif chip_id == "weekly_review":
        wk = ctx.get("weekly") or {}
        parts.append(f"**이번 주 훈련 리뷰**\n- 점수: {wk.get('total_score', '-')}\n"
                     f"- 거리: {wk.get('total_distance_km', '-')}km\n"
                     f"- 횟수: {wk.get('run_count', '-')}회")
    elif chip_id == "recovery_advice":
        rec = ctx.get("recovery") or {}
        grade = rec.get("grade", "정보 없음")
        parts.append(f"**회복 상태**: {grade}\n\n"
                     "충분한 수면과 수분 섭취를 유지하세요. "
                     "바디 배터리가 50 이하라면 저강도 훈련을 권장합니다.")
    elif chip_id == "injury_risk":
        acwr = ctx.get("acwr") or {}
        avg = (acwr.get("average") or {}) if acwr else {}
        status = avg.get("status", "정보 없음")
        parts.append(f"**부상 위험 분석**\n- ACWR 상태: {status}\n\n"
                     "ACWR이 1.3 이상이면 부하 급증 위험이 있습니다. "
                     "훈련량을 10% 이내로 점진적으로 늘리세요.")
    else:
        # 일반 질문
        fit = ctx.get("fitness") or {}
        rec = ctx.get("recovery") or {}
        parts.append("**현재 상태 요약**")
        if fit.get("tsb") is not None:
            parts.append(f"- TSB(신선도): {fit['tsb']:+.1f}")
        if rec.get("grade"):
            parts.append(f"- 회복 등급: {rec['grade']}")
        goal = ctx.get("goal")
        if goal:
            parts.append(f"- 목표: {goal.get('name', '-')} ({goal.get('distance_km', '-')}km)")
        parts.append("\n궁금한 점이 더 있으시면 질문해주세요!")

    return "\n".join(parts) if parts else "데이터가 충분하지 않아 분석이 어렵습니다. 동기화 후 다시 시도해주세요."


def _call_claude(prompt: str, config: dict | None) -> str:
    """Claude API 호출 (향후 구현)."""
    api_key = (config or {}).get("ai", {}).get("claude_api_key", "")
    if not api_key:
        return "Claude API 키가 설정되지 않았습니다. 설정 > AI에서 키를 입력하세요."
    try:
        import httpx
        resp = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 1024,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["content"][0]["text"]
    except Exception as exc:
        log.warning("Claude API 오류: %s", exc)
        return f"AI 응답 생성 실패: {exc}"


def _call_openai(prompt: str, config: dict | None) -> str:
    """OpenAI API 호출 (향후 구현)."""
    api_key = (config or {}).get("ai", {}).get("openai_api_key", "")
    if not api_key:
        return "OpenAI API 키가 설정되지 않았습니다."
    try:
        import httpx
        resp = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 1024,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except Exception as exc:
        log.warning("OpenAI API 오류: %s", exc)
        return f"AI 응답 생성 실패: {exc}"


def _call_genspark(prompt: str, config: dict | None) -> str:
    """Genspark API 호출 (무료, 향후 구현)."""
    return ("Genspark 연동은 아직 구현되지 않았습니다. "
            "config.json에서 ai.provider를 'claude' 또는 'openai'로 변경하세요.")
