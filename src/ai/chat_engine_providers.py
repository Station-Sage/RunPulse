"""AI 채팅 — 외부 API provider 호출 모듈.

chat_engine.py에서 분리. Claude, OpenAI, Gemini, Groq, Genspark 등 외부 AI API 호출.
`complete()`는 실패를 ProviderError(reason·http_status)로 올린다 — 조용히 삼키지 않는다(design §6.2).
`call_claude` 등 단순 호출은 기존 호출자(ai_message·today 내러티브) 호환을 위해 실패 문자열/RateLimitError를 유지한다.
"""
from __future__ import annotations

import json
import logging
import sqlite3

from .provider_common import (
    ENDPOINTS, ProviderError, RateLimitError, api_key_for, check_response, model_for,
    timeout_for, wrap_transport_error,
)

log = logging.getLogger(__name__)
__all__ = ["ProviderError", "RateLimitError", "complete", "call_with_tools"]


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
    "- 특정 날짜 활동 조회 → get_activity\n"
    "- 기간 내 활동 목록 → get_activities_range\n"
    "- 특정 날짜 메트릭 → get_metrics\n"
    "- 메트릭 추세 → get_metrics_trend\n"
    "- 특정 날짜 날씨 → get_weather\n"
    "- 웰니스(수면, HRV, 스트레스) 기간 데이터 → get_wellness\n"
    "- 피트니스 추이(CTL, ATL, TSB) → get_fitness\n"
    "- 레이스 기록 → get_race_history\n"
    "- 기간별 비교 → compare_periods\n"
    "- 훈련 계획 → get_training_plan\n"
    "- 러너 프로필 → get_runner_profile\n"
    "- 훈련 기간·블록·대회 이후 요약 → get_training_summary (기간 질문의 첫 호출)\n"
    "- 인터벌·크루즈 세트별 랩 데이터 → get_activity_laps (activity_id는 정수)\n"
    "- 세션 간 세트 페이스 비교 → compare_workout_sets\n\n"
    "## 중요 규칙\n"
    "- 컨텍스트에 평균 페이스/심박만 있어도, 사용자가 '구간별', 'km별', '스플릿', '상세' 등을 요청하면 반드시 도구를 호출하세요.\n"
    "- 도구를 호출하지 않고 '데이터가 없습니다'라고 답하지 마세요.\n"
    "- activity_id는 컨텍스트에 포함된 정수 ID를 사용하세요.\n"
    "- 한국어로 답변하세요."
)


def _post(url: str, headers: dict, body: dict, deadline: float | None, provider: str) -> dict:
    import httpx
    try:
        resp = httpx.post(url, headers=headers, json=body, timeout=timeout_for(deadline))
        check_response(resp, provider)
        return resp.json()
    except ProviderError:
        raise
    except Exception as exc:
        raise wrap_transport_error(exc) from exc


def _non_empty(text, provider: str) -> str:
    if not text or not str(text).strip():
        raise ProviderError("parse_error", None, f"{provider} empty response")
    return text


def complete(provider: str, prompt: str, config: dict | None, *, conn: sqlite3.Connection | None = None,
             tools: bool = False, deadline: float | None = None, stats: dict | None = None) -> str:
    """provider 1곳 호출. tools=True면 함수 호출 루프(conn 필요). 실패는 ProviderError. stats['tool_calls']에 조회 횟수를 센다."""
    key = api_key_for(provider, config)
    if provider not in ENDPOINTS or not key:
        raise ProviderError("no_key")
    ai_cfg = (config or {}).get("ai", {})
    temp = ai_cfg.get("_temperature", 0.7)
    model = model_for(provider, config)
    if tools and conn is not None:
        from .tools import TOOL_DECLARATIONS, execute_tool as _execute
        stats = stats if stats is not None else {}

        def execute_tool(*args, **kwargs):
            stats["tool_calls"] = stats.get("tool_calls", 0) + 1
            return _execute(*args, **kwargs)
        if provider == "claude":
            return _call_claude_with_tools(conn, prompt, ENDPOINTS[provider], key, model,
                                           TOOL_DECLARATIONS, execute_tool, temp, deadline)
        return _openai_compat_loop(conn, prompt, provider, key, model, TOOL_DECLARATIONS,
                                   execute_tool, temp, deadline)
    if provider == "claude":
        data = _post(ENDPOINTS[provider], _claude_headers(key),
                     {"model": model, "max_tokens": 1024, "temperature": temp,
                      "messages": [{"role": "user", "content": prompt}]}, deadline, provider)
        try:
            return _non_empty(data["content"][0]["text"], provider)
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError("parse_error", None, "claude") from exc
    data = _post(ENDPOINTS[provider], _bearer(key),
                 {"model": model, "messages": [{"role": "user", "content": prompt}],
                  "max_tokens": 2048, "temperature": temp}, deadline, provider)
    try:
        return _non_empty(data["choices"][0]["message"]["content"], provider)
    except (KeyError, IndexError, TypeError) as exc:
        raise ProviderError("parse_error", None, provider) from exc


def _bearer(key: str) -> dict:
    return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}


def _claude_headers(key: str) -> dict:
    return {"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"}


def call_with_tools(conn: sqlite3.Connection, prompt: str, config: dict | None, provider: str,
                    deadline: float | None = None) -> str:
    """모든 provider 공통 tool calling — 실패는 ProviderError(RateLimitError 포함)."""
    return complete(provider, prompt, config, conn=conn, tools=True, deadline=deadline)


def _openai_compat_loop(conn, prompt, provider, key, model, declarations, execute_tool, temp, deadline) -> str:
    tools = _gemini_to_openai_tools(declarations)
    messages = [{"role": "system", "content": _TOOL_SYSTEM_TEXT}, {"role": "user", "content": prompt}]
    msg: dict = {}
    for _ in range(3):
        data = _post(ENDPOINTS[provider], _bearer(key),
                     {"model": model, "messages": messages, "tools": tools, "tool_choice": "auto",
                      "max_tokens": 2048, "temperature": temp}, deadline, provider)
        try:
            msg = data["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError("parse_error", None, provider) from exc
        if not msg.get("tool_calls"):
            return _non_empty(msg.get("content"), provider)
        messages.append(msg)
        for tc in msg["tool_calls"]:
            fn_name = tc["function"]["name"]
            try:
                fn_args = json.loads(tc["function"]["arguments"])
            except (ValueError, TypeError):
                fn_args = {}
            log.info("%s 도구 호출: %s(%s)", provider, fn_name, fn_args)
            messages.append({"role": "tool", "tool_call_id": tc["id"], "name": fn_name,
                             "content": execute_tool(conn, fn_name, fn_args)})
    return _non_empty(msg.get("content"), provider)


def _call_claude_with_tools(conn, prompt, url, key, model, tool_declarations, execute_tool, temp, deadline) -> str:
    """Claude Messages API tool calling."""
    claude_tools = [
        {"name": d["name"], "description": d.get("description", ""),
         "input_schema": d.get("parameters", {"type": "object", "properties": {}})}
        for d in tool_declarations
    ]
    messages = [{"role": "user", "content": prompt}]
    text_parts: list[str] = []
    for _ in range(3):
        data = _post(url, _claude_headers(key),
                     {"model": model, "system": _TOOL_SYSTEM_TEXT, "max_tokens": 2048,
                      "temperature": temp, "tools": claude_tools, "messages": messages},
                     deadline, "claude")
        text_parts, tool_uses = [], []
        for block in data.get("content", []):
            if block.get("type") == "text":
                text_parts.append(block["text"])
            elif block.get("type") == "tool_use":
                tool_uses.append(block)
        if not tool_uses:
            break
        messages.append({"role": "assistant", "content": data["content"]})
        results = []
        for tu in tool_uses:
            log.info("Claude 도구 호출: %s(%s)", tu["name"], tu["input"])
            results.append({"type": "tool_result", "tool_use_id": tu["id"],
                            "content": execute_tool(conn, tu["name"], tu["input"])})
        messages.append({"role": "user", "content": results})
    return _non_empty("\n".join(text_parts), "claude")


# ── 단순 호출 (기존 호출자 호환: 실패는 문자열, 429만 RateLimitError) ──────

_KEY_HELP = {
    "claude": "Claude API 키가 설정되지 않았습니다. ☰ 설정 → AI 코치에서 키를 입력하세요.",
    "openai": "OpenAI API 키가 설정되지 않았습니다.",
    "gemini": "Gemini API 키가 설정되지 않았습니다. ☰ 설정 → AI 코치에서 키를 입력하세요.\n발급: https://aistudio.google.com/apikey",
    "groq": "Groq API 키가 설정되지 않았습니다. ☰ 설정 → AI 코치에서 키를 입력하세요.\n발급: https://console.groq.com/keys",
}
_LABEL = {"claude": "Claude", "openai": "OpenAI", "gemini": "Gemini", "groq": "Groq"}


def _simple(provider: str, prompt: str, config: dict | None) -> str:
    if not api_key_for(provider, config):
        return _KEY_HELP[provider]
    try:
        return complete(provider, prompt, config)
    except RateLimitError:
        raise
    except ProviderError as exc:
        log.warning("%s API 오류: %s", provider, exc)
        return f"{_LABEL[provider]} 응답 생성 실패: {exc}"


def call_claude(prompt: str, config: dict | None) -> str:
    return _simple("claude", prompt, config)


def call_openai(prompt: str, config: dict | None) -> str:
    return _simple("openai", prompt, config)


def call_gemini(prompt: str, config: dict | None) -> str:
    return _simple("gemini", prompt, config)


def call_groq(prompt: str, config: dict | None) -> str:
    return _simple("groq", prompt, config)


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
