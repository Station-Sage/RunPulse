"""코치 체인의 claude_queue 선두 처리·진행 콜백·tool_names 수집 테스트."""
import json

from src.ai import provider_claude_queue as pcq
from src.ai.chat_engine_result import build_chain
from src.ai.provider_common import CLAUDE_QUEUE, ProviderError
from src.ai_worker import cli_runner as cr

CFG = {"gemini_api_key": "k"}


def test_chain_cq_leads_with_fallback():
    consent = {"provider": CLAUDE_QUEUE, "fallback_enabled": True}
    chain, why = build_chain(CLAUDE_QUEUE, CFG, consent, True, cq_available=True)
    assert chain[0] == CLAUDE_QUEUE and why is None


def test_chain_cq_unavailable_no_fallback_is_empty():
    chain, why = build_chain(CLAUDE_QUEUE, CFG, {"provider": CLAUDE_QUEUE}, True, cq_available=False)
    assert chain == [] and why == "no_key"


def test_chain_cq_requires_consent():
    assert build_chain(CLAUDE_QUEUE, CFG, None, True, cq_available=True) == ([], "no_consent")


def test_complete_coach_maps_progress(monkeypatch):
    calls, stats = [], {}

    def fake(conn, config, **kw):
        kw["on_progress"](json.dumps({"tools": ["get_fitness"]}), "a")
        kw["on_progress"](json.dumps({"tools": ["get_fitness", "get_fitness"]}), "ab")
        return "ok"
    monkeypatch.setattr(pcq, "complete", fake)
    assert pcq.complete_coach(object(), "q", {}, stats, calls.append, {}) == "ok"
    assert calls == ["get_fitness", "get_fitness"] and stats["tool_calls"] == 2


def test_complete_coach_no_conn():
    try:
        pcq.complete_coach(None, "q", {}, None, None, {})
    except ProviderError as e:
        assert e.reason == "no_key"


def test_feed_collects_tool_names():
    res = cr.RunResult()
    cr.feed(res, {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "name": "mcp__runpulse__get_fitness"}]}})
    assert res.tool_names == ["get_fitness"] and res.tool_calls == 1
