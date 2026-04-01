"""AI 채팅 — 외부 API provider 호출 모듈.

chat_engine.py에서 분리. Claude, OpenAI, Gemini, Groq, Genspark 등
외부 AI API 호출 함수.
"""
from __future__ import annotations

import logging
import sqlite3
from typing import Any

log = logging.getLogger(__name__)


class RateLimitError(Exception):
    """429 Too Many Requests — provider 전환 트리거."""
    pass


def call_claude(prompt: str, config: dict | None) -> str:
    """Claude API 호출."""
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


def call_openai(prompt: str, config: dict | None) -> str:
    """OpenAI API 호출."""
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


def call_gemini_with_tools(conn: sqlite3.Connection, prompt: str,
                           config: dict | None) -> str | None:
    """Gemini Function Calling — AI가 도구를 호출하여 DB 데이터 수집 후 답변."""
    api_key = (config or {}).get("ai", {}).get("gemini_api_key", "")
    if not api_key:
        return None
    model = (config or {}).get("ai", {}).get("gemini_model", "gemini-2.0-flash")
    temp = (config or {}).get("ai", {}).get("_temperature", 0.7)

    from .tools import TOOL_DECLARATIONS, execute_tool
    try:
        import httpx

        system_text = (
            "당신은 러닝 AI 코치입니다. 사용자의 질문에 정확히 답하기 위해 도구를 적극 활용하세요.\n"
            "- km별 페이스, 스플릿, 심박존, 케이던스, 파워 등 상세 데이터 → get_activity_detail 호출\n"
            "- 특정 날짜 날씨 → get_weather 호출\n"
            "- 웰니스(수면, HRV, 스트레스) → get_wellness 호출\n"
            "- 피트니스 추이(CTL, ATL, TSB) → get_fitness_trend 호출\n"
            "- 레이스 기록 → get_race_history 호출\n"
            "- 기간별 비교 → get_period_comparison 호출\n"
            "컨텍스트에 요약 데이터만 있고 상세가 필요하면, 반드시 도구를 호출하세요."
        )
        contents = [{"parts": [{"text": prompt}]}]
        body: dict = {
            "systemInstruction": {"parts": [{"text": system_text}]},
            "contents": contents,
            "tools": [{"function_declarations": TOOL_DECLARATIONS}],
            "generationConfig": {"maxOutputTokens": 2048, "temperature": temp},
        }

        max_rounds = 3
        for _ in range(max_rounds):
            resp = httpx.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                params={"key": api_key},
                headers={"Content-Type": "application/json"},
                json=body, timeout=60,
            )
            if resp.status_code == 429:
                raise RateLimitError("Gemini 429")
            resp.raise_for_status()
            data = resp.json()

            candidates = data.get("candidates", [])
            if not candidates:
                return None

            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts:
                return None

            text_parts = [p["text"] for p in parts if "text" in p]
            func_calls = [p["functionCall"] for p in parts if "functionCall" in p]

            if not func_calls:
                return text_parts[0] if text_parts else None

            contents.append({"role": "model", "parts": parts})

            func_response_parts = []
            for fc in func_calls:
                fn_name = fc["name"]
                fn_args = fc.get("args", {})
                log.info("Gemini 도구 호출: %s(%s)", fn_name, fn_args)
                result_json = execute_tool(conn, fn_name, fn_args)
                func_response_parts.append({
                    "functionResponse": {
                        "name": fn_name,
                        "response": {"content": result_json},
                    }
                })

            contents.append({"parts": func_response_parts})
            body["contents"] = contents

        log.warning("Gemini function calling %d회 초과", max_rounds)
        return text_parts[0] if text_parts else None

    except RateLimitError:
        raise
    except Exception as exc:
        log.warning("Gemini function calling 실패: %s", exc)
        return None


def call_gemini(prompt: str, config: dict | None) -> str:
    """Google Gemini API 호출 (무료 tier). 429 시 RateLimitError."""
    api_key = (config or {}).get("ai", {}).get("gemini_api_key", "")
    if not api_key:
        return "Gemini API 키가 설정되지 않았습니다. 설정 > AI에서 키를 입력하세요.\n발급: https://aistudio.google.com/apikey"
    model = (config or {}).get("ai", {}).get("gemini_model", "gemini-2.0-flash")
    temp = (config or {}).get("ai", {}).get("_temperature", 0.7)
    try:
        import httpx
        resp = httpx.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            params={"key": api_key},
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "maxOutputTokens": 2048,
                    "temperature": temp,
                },
            },
            timeout=60,
        )
        if resp.status_code == 429:
            log.warning("Gemini 429 Too Many Requests")
            raise RateLimitError("Gemini 429")
        resp.raise_for_status()
        data = resp.json()
        candidates = data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            if parts:
                return parts[0].get("text", "빈 응답")
        return "Gemini에서 빈 응답을 받았습니다."
    except RateLimitError:
        raise
    except Exception as exc:
        log.warning("Gemini API 오류: %s", exc)
        return f"Gemini 응답 생성 실패: {exc}"


def call_groq(prompt: str, config: dict | None) -> str:
    """Groq API 호출 (무료 tier, Llama 3.3 70B 등). 429 시 RateLimitError."""
    api_key = (config or {}).get("ai", {}).get("groq_api_key", "")
    if not api_key:
        return "Groq API 키가 설정되지 않았습니다. 설정 > AI에서 키를 입력하세요.\n발급: https://console.groq.com/keys"
    model = (config or {}).get("ai", {}).get("groq_model", "llama-3.3-70b-versatile")
    temp = (config or {}).get("ai", {}).get("_temperature", 0.7)
    try:
        import httpx
        resp = httpx.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 2048,
                "temperature": temp,
            },
            timeout=60,
        )
        if resp.status_code == 429:
            log.warning("Groq 429 Too Many Requests")
            raise RateLimitError("Groq 429")
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except RateLimitError:
        raise
    except Exception as exc:
        log.warning("Groq API 오류: %s", exc)
        return f"Groq 응답 생성 실패: {exc}"


def call_genspark(prompt: str, config: dict | None) -> str:
    """Genspark 수동 모드 — 프롬프트를 준비하고 사용자가 붙여넣기."""
    call_genspark._last_prompt = prompt
    return (
        "📋 **프롬프트가 준비되었습니다.**\n\n"
        "1. 아래 '프롬프트 복사' 버튼을 클릭하세요\n"
        "2. [Genspark AI 채팅](https://www.genspark.ai/agents?type=ai_chat)을 열어 붙여넣으세요\n"
        "3. AI 응답을 받으면 '응답 붙여넣기'에 입력하세요"
    )

call_genspark._last_prompt = ""


def call_genspark_selenium(prompt: str, config: dict | None) -> str:
    """Genspark 자동 모드 — proot + Selenium으로 DOM 자동화."""
    try:
        from src.ai.genspark_driver import send_and_receive
        return send_and_receive(prompt)
    except ImportError:
        return ("Genspark 자동 모드에는 proot + Selenium 설정이 필요합니다.\n"
                "설정 → AI에서 'genspark' (수동 모드)로 변경하세요.")
    except Exception as exc:
        log.warning("Genspark Selenium 오류: %s", exc)
        return f"Genspark 자동 모드 오류: {exc}"
