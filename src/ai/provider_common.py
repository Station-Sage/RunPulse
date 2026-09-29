"""AI provider 공통 — 구조화 오류(ProviderError), 모델 ID 해석, 타임아웃(30-coach-chat design §4.3·§6.2).

모델 ID는 이 파일의 DEFAULT_MODELS(유일한 기본값) + config["ai"]["<provider>_model"] 오버라이드로만 정해진다.
"""
from __future__ import annotations

import time

DEFAULT_MODELS = {
    "gemini": "gemini-2.5-flash",
    "groq": "llama-3.3-70b-versatile",
    "openai": "gpt-4o-mini",
    "claude": "claude-sonnet-4-5",
}
ENDPOINTS = {
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
    "groq": "https://api.groq.com/openai/v1/chat/completions",
    "openai": "https://api.openai.com/v1/chat/completions",
    "claude": "https://api.anthropic.com/v1/messages",
}
KEY_FIELDS = {p: f"{p}_api_key" for p in DEFAULT_MODELS}
LLM_PROVIDERS = tuple(DEFAULT_MODELS)

CONNECT_TIMEOUT = 10.0
READ_TIMEOUT = 30.0
TOTAL_BUDGET = 45.0

REASON_LABELS = {
    "http_404": "연결 실패(404)", "http_401": "인증 실패(401)", "http_429": "사용량 한도(429)",
    "timeout": "시간 초과", "no_key": "키 없음", "parse_error": "응답 해석 실패", "user_skip": "사용자 선택",
    "no_consent": "동의 필요", "network": "네트워크 오류", "http_5xx": "서버 오류(5xx)",
}


class ProviderError(Exception):
    """provider 호출 실패 — reason은 design §6.2의 코드(http_404/http_401/http_429/timeout/no_key/parse_error/http_5xx 등)."""

    def __init__(self, reason: str, http_status: int | None = None, detail: str = ""):
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason = reason
        self.http_status = http_status
        self.detail = detail


class RateLimitError(ProviderError):
    """429 Too Many Requests — provider 전환 트리거."""

    def __init__(self, detail: str = ""):
        super().__init__("http_429", 429, detail)


def model_for(provider: str, config: dict | None) -> str:
    cfg = ((config or {}).get("ai") or {}).get(f"{provider}_model")
    return cfg or DEFAULT_MODELS.get(provider, "")


def api_key_for(provider: str, config: dict | None) -> str:
    return ((config or {}).get("ai") or {}).get(KEY_FIELDS.get(provider, ""), "") or ""


def reason_for_status(status: int) -> str:
    if status in (401, 403):
        return "http_401"
    return f"http_{status}" if status in (404, 429) else f"http_{status // 100}xx"


def check_response(resp, provider: str) -> None:
    """HTTP 응답을 검사해 4xx/5xx면 ProviderError(429는 RateLimitError)."""
    status = resp.status_code
    if status == 429:
        raise RateLimitError(provider)
    if status >= 400:
        raise ProviderError(reason_for_status(status), status, provider)


def timeout_for(deadline: float | None):
    """호출 1회의 httpx.Timeout — 연결 10s·응답 30s, 전체 마감(monotonic)까지 남은 시간으로 상한."""
    import httpx
    remaining = READ_TIMEOUT if deadline is None else deadline - time.monotonic()
    if remaining <= 0:
        raise ProviderError("timeout", None, "budget exhausted")
    return httpx.Timeout(min(READ_TIMEOUT, remaining), connect=min(CONNECT_TIMEOUT, remaining))


def wrap_transport_error(exc: Exception) -> ProviderError:
    """httpx 전송 오류(타임아웃·연결) → ProviderError."""
    import httpx
    if isinstance(exc, ProviderError):
        return exc
    if isinstance(exc, httpx.TimeoutException):
        return ProviderError("timeout", None, type(exc).__name__)
    if isinstance(exc, (KeyError, IndexError, ValueError, TypeError)):
        return ProviderError("parse_error", None, type(exc).__name__)
    return ProviderError("network", None, type(exc).__name__)
