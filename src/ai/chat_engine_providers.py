"""AI 채팅 — 외부 API provider 호출 모듈.

chat_engine.py에서 분리. Claude, OpenAI, Gemini, Groq, Genspark 등
외부 AI API 호출 함수.
"""
from __future__ import annotations

import json
import logging
import sqlite3
from typing import Any

log = logging.getLogger(__name__)


class RateLimitError(Exception):
    """429 Too Many Requests — provider 전환 트리거."""
    pass


# ── 공통 Tool Calling ────────────────────────────────────────────────

def _gemini_to_openai_tools(declarations: list[dict]) -> list[dict]:
    """Gemini function_declarations → OpenAI tools 형식 변환."""
    return [
        {
            "type": "function",
            "function": {
                "name": d["name"],
                "description": d.get("description", ""),
                "parameters": d.get("parameters", {"type": "object", "properties": {}}),
            },
        }
        for d in declarations
    ]


_TOOL_SYSTEM_TEXT = (
    "당신은 러닝 AI 코치입니다. 사용자의 질문에 정확히 답하기 위해 도구를 적극 활용하세요.\n\n"
    "## 반드시 도구를 호출해야 하는 경우\n"
    "- km별 페이스, 스플릿, 구간별 데이터 → get_activity_detail (activity_id는 정수)\n"
    "- 심박존 분포, 케이던스, 파워 상세 → get_activity_detail\n"
    "- 특정 날짜 날씨 → get_weather\n"
    "- 웰니스(수면, HRV, 스트레스) 기간 데이터 → get_wellness\n"
    "- 피트니스 추이(CTL, ATL, TSB) → get_fitness_trend\n"
    "- 레이스 기록 → get_race_history\n"
    "- 기간별 비교 → get_period_comparison\n\n"
    "## 중요 규칙\n"
    "- 컨텍스트에 평균 페이스/심박만 있어도, 사용자가 '구간별', 'km별', '스플릿', '상세' 등을 요청하면 반드시 도구를 호출하세요.\n"
    "- 도구를 호출하지 않고 '데이터가 없습니다'라고 답하지 마세요.\n"
    "- activity_id는 컨텍스트에 포함된 정수 ID를 사용하세요.\n"
    "- 한국어로 답변하세요."
)


def call_with_tools(conn: sqlite3.Connection, prompt: str,
                    config: dict | None, provider: str) -> str | None:
    """모든 provider 공통 tool calling 함수."""
    ai_cfg = (config or {}).get("ai", {})

    PROVIDER_CONFIG = {
        "gemini": {
            "url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
            "key": ai_cfg.get("gemini_api_key", ""),
            "model": ai_cfg.get("gemini_model", "gemini-2.0-flash"),
        },
        "groq": {
            "url": "https://api.groq.com/openai/v1/chat/completions",
            "key": ai_cfg.get("groq_api_key", ""),
            "model": ai_cfg.get("groq_model", "llama-3.3-70b-versatile"),
        },
        "openai": {
            "url": "https://api.openai.com/v1/chat/completions",
            "key": ai_cfg.get("openai_api_key", ""),
            "model": ai_cfg.get("openai_model", "gpt-4o-mini"),
        },
        "claude": {
            "url": "https://api.anthropic.com/v1/messages",
            "key": ai_cfg.get("claude_api_key", ""),
            "model": ai_cfg.get("claude_model", "claude-sonnet-4-20250514"),
        },
    }

    pcfg = PROVIDER_CONFIG.get(provider)
    if not pcfg or not pcfg["key"]:
        return None

    from .tools import TOOL_DECLARATIONS, execute_tool
    temp = ai_cfg.get("_temperature", 0.7)

    # Claude는 API 형식이 다름
    if provider == "claude":
        return _call_claude_with_tools(
            conn, prompt, pcfg, TOOL_DECLARATIONS, execute_tool, temp
        )

    # Gemini / Groq / OpenAI — OpenAI 호환 공통
    try:
        import httpx

        tools = _gemini_to_openai_tools(TOOL_DECLARATIONS)
        messages = [
            {"role": "system", "content": _TOOL_SYSTEM_TEXT},
            {"role": "user", "content": prompt},
        ]

        max_rounds = 3
        for _ in range(max_rounds):
            resp = httpx.post(
                pcfg["url"],
                headers={
                    "Authorization": f"Bearer {pcfg['key']}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": pcfg["model"],
                    "messages": messages,
                    "tools": tools,
                    "tool_choice": "auto",
                    "max_tokens": 2048,
                    "temperature": temp,
                },
                timeout=60,
            )
            if resp.status_code == 429:
                raise RateLimitError(f"{provider} 429")
            resp.raise_for_status()
            data = resp.json()

            msg = data["choices"][0]["message"]
            if not msg.get("tool_calls"):
                return msg.get("content", "")

            messages.append(msg)
            for tc in msg["tool_calls"]:
                fn_name = tc["function"]["name"]
                fn_args = json.loads(tc["function"]["arguments"])
                log.info("%s 도구 호출: %s(%s)", provider, fn_name, fn_args)
                result_json = execute_tool(conn, fn_name, fn_args)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "name": fn_name,
                    "content": result_json,
                })

        return msg.get("content", "")

    except RateLimitError:
        raise
    except Exception as exc:
        log.warning("%s tool calling 실패: %s", provider, exc)
        return None


def _call_claude_with_tools(conn, prompt, pcfg, tool_declarations,
                            execute_tool, temp):
    """Claude Messages API tool calling."""
    import httpx

    claude_tools = [
        {
            "name": d["name"],
            "description": d.get("description", ""),
            "input_schema": d.get("parameters", {"type": "object", "properties": {}}),
        }
        for d in tool_declarations
    ]

    messages = [{"role": "user", "content": prompt}]

    max_rounds = 3
    text_parts = []
    for _ in range(max_rounds):
        resp = httpx.post(
            pcfg["url"],
            headers={
                "x-api-key": pcfg["key"],
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": pcfg["model"],
                "system": _TOOL_SYSTEM_TEXT,
                "max_tokens": 2048,
                "temperature": temp,
                "tools": claude_tools,
                "messages": messages,
            },
            timeout=60,
        )
        if resp.status_code == 429:
            raise RateLimitError("Claude 429")
        resp.raise_for_status()
        data = resp.json()

        text_parts = []
        tool_uses = []
        for block in data.get("content", []):
            if block["type"] == "text":
                text_parts.append(block["text"])
            elif block["type"] == "tool_use":
                tool_uses.append(block)

        if not tool_uses:
            return "\n".join(text_parts) if text_parts else None

        messages.append({"role": "assistant", "content": data["content"]})
        tool_results = []
        for tu in tool_uses:
            log.info("Claude 도구 호출: %s(%s)", tu["name"], tu["input"])
            result_json = execute_tool(conn, tu["name"], tu["input"])
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tu["id"],
                "content": result_json,
            })
        messages.append({"role": "user", "content": tool_results})

    return "\n".join(text_parts) if text_parts else None


# ── 단순 호출 (tool calling 없이, fallback용) ────────────────────────

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


def call_gemini(prompt: str, config: dict | None) -> str:
    """Google Gemini API 호출 (tool calling 없이). 429 시 RateLimitError."""
    api_key = (config or {}).get("ai", {}).get("gemini_api_key", "")
    if not api_key:
        return "Gemini API 키가 설정되지 않았습니다. 설정 > AI에서 키를 입력하세요.\n발급: https://aistudio.google.com/apikey"
    model = (config or {}).get("ai", {}).get("gemini_model", "gemini-2.0-flash")
    temp = (config or {}).get("ai", {}).get("_temperature", 0.7)
    try:
        import httpx
        resp = httpx.post(
            f"https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
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
            log.warning("Gemini 429 Too Many Requests")
            raise RateLimitError("Gemini 429")
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except RateLimitError:
        raise
    except Exception as exc:
        log.warning("Gemini API 오류: %s", exc)
        return f"Gemini 응답 생성 실패: {exc}"


def call_groq(prompt: str, config: dict | None) -> str:
    """Groq API 호출 (tool calling 없이). 429 시 RateLimitError."""
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
