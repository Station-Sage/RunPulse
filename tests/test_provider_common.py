"""provider 오류 구조화(30-coach-chat design §6.2) — HTTP 상태→reason 매핑, 모델 ID 설정화, 타임아웃."""
import time

import httpx
import pytest

from src.ai import chat_engine_providers as prov
from src.ai.provider_common import (
    DEFAULT_MODELS, ProviderError, RateLimitError, model_for, reason_for_status, timeout_for,
)

CFG = {"ai": {"gemini_api_key": "k", "groq_api_key": "k2"}}


class _Resp:
    def __init__(self, status, payload=None):
        self.status_code = status
        self._p = payload or {}

    def json(self):
        return self._p


def _ok(text="안녕"):
    return _Resp(200, {"choices": [{"message": {"content": text}}]})


@pytest.mark.parametrize("status,reason", [(404, "http_404"), (401, "http_401"), (403, "http_401"), (500, "http_5xx")])
def test_status_maps_to_reason(monkeypatch, status, reason):
    monkeypatch.setattr(httpx, "post", lambda *a, **k: _Resp(status))
    with pytest.raises(ProviderError) as ei:
        prov.complete("gemini", "hi", CFG)
    assert ei.value.reason == reason and ei.value.http_status == status
    assert reason_for_status(status) == reason


def test_429_is_rate_limit_error(monkeypatch):
    monkeypatch.setattr(httpx, "post", lambda *a, **k: _Resp(429))
    with pytest.raises(RateLimitError) as ei:
        prov.complete("groq", "hi", CFG)
    assert ei.value.reason == "http_429"


def test_timeout_maps_to_timeout(monkeypatch):
    def boom(*a, **k):
        raise httpx.ReadTimeout("slow")
    monkeypatch.setattr(httpx, "post", boom)
    with pytest.raises(ProviderError) as ei:
        prov.complete("gemini", "hi", CFG)
    assert ei.value.reason == "timeout"


def test_no_key_and_empty_response(monkeypatch):
    with pytest.raises(ProviderError) as ei:
        prov.complete("claude", "hi", CFG)
    assert ei.value.reason == "no_key"
    monkeypatch.setattr(httpx, "post", lambda *a, **k: _ok("  "))
    with pytest.raises(ProviderError) as ei:
        prov.complete("gemini", "hi", CFG)
    assert ei.value.reason == "parse_error"


def test_success_uses_config_model_only(monkeypatch):
    seen = {}

    def fake(url, headers=None, json=None, timeout=None):
        seen["model"] = json["model"]
        return _ok()
    monkeypatch.setattr(httpx, "post", fake)
    assert prov.complete("gemini", "hi", CFG) == "안녕"
    assert seen["model"] == DEFAULT_MODELS["gemini"] == "gemini-2.5-flash"
    prov.complete("gemini", "hi", {"ai": {"gemini_api_key": "k", "gemini_model": "my-model"}})
    assert seen["model"] == "my-model"
    assert model_for("groq", None) == DEFAULT_MODELS["groq"]


def test_deadline_exhausted_raises_timeout():
    with pytest.raises(ProviderError) as ei:
        timeout_for(time.monotonic() - 1)
    assert ei.value.reason == "timeout"
    t = timeout_for(time.monotonic() + 5)
    assert t.read <= 5 and t.connect <= 5


def test_legacy_call_keeps_string_contract(monkeypatch):
    assert "설정되지 않았습니다" in prov.call_claude("hi", {})
    monkeypatch.setattr(httpx, "post", lambda *a, **k: _Resp(404))
    assert "실패" in prov.call_gemini("hi", CFG)
    monkeypatch.setattr(httpx, "post", lambda *a, **k: _Resp(429))
    with pytest.raises(RateLimitError):
        prov.call_groq("hi", CFG)


def test_tool_loop_executes_tool_then_answers(monkeypatch):
    calls = iter([
        _Resp(200, {"choices": [{"message": {"content": None, "tool_calls": [
            {"id": "1", "function": {"name": "get_fitness", "arguments": "{}"}}]}}]}),
        _ok("최종"),
    ])
    monkeypatch.setattr(httpx, "post", lambda *a, **k: next(calls))
    import src.ai.tools as tools
    monkeypatch.setattr(tools, "execute_tool", lambda conn, n, a: "{}")
    assert prov.call_with_tools(object(), "hi", CFG, "gemini") == "최종"
