"""chat_result on_event/cancelled 훅 — 비동기 답변 단계 이벤트(30-coach-chat design §6.2)."""
import httpx

from src.ai import chat_engine_result as cer
from src.ai.chat_engine import chat_result

CFG = {"ai": {"provider": "gemini", "gemini_api_key": "k", "groq_api_key": "k2"}}
CONSENT = {"provider": "gemini", "exclude_notes": False, "tools_enabled": False, "fallback_enabled": True}


class _Resp:
    def __init__(self, status, text="답변"):
        self.status_code = status
        self._p = {"choices": [{"message": {"content": text}}]}

    def json(self):
        return self._p


def test_stage_events_per_provider_and_rule(db_conn, monkeypatch):
    monkeypatch.setattr(httpx, "post", lambda *a, **k: _Resp(404))
    events = []
    chat_result(db_conn, "안녕", CFG, consent=CONSENT, require_consent=True,
                on_event=lambda name, p: events.append((name, p["key"], p.get("provider"))))
    assert events == [("stage", "model", "gemini"), ("stage", "model", "groq"), ("stage", "rule", None)]


def test_cancelled_stops_chain_before_next_provider(db_conn, monkeypatch):
    monkeypatch.setattr(httpx, "post", lambda *a, **k: _Resp(404))
    seen = []

    def on_event(name, p):
        seen.append(p.get("provider"))
    cancel = {"on": False}

    def _on(name, p):
        on_event(name, p)
        cancel["on"] = True
    chat_result(db_conn, "안녕", CFG, consent=CONSENT, require_consent=True,
                on_event=_on, cancelled=lambda: cancel["on"])
    assert seen[0] == "gemini" and "groq" not in seen


def test_tool_stage_emitted(db_conn, monkeypatch):
    def fake_complete(prov, prompt, config, *, conn=None, tools=False, deadline=None, stats=None, on_tool=None):
        on_tool("get_fitness")
        return "ok"
    monkeypatch.setattr(cer, "complete", fake_complete)
    events = []
    chat_result(db_conn, "안녕", CFG, consent={**CONSENT, "tools_enabled": True}, require_consent=True,
                on_event=lambda n, p: events.append(p))
    assert {"key": "tool", "label": "데이터 확인 중: get_fitness", "tool": "get_fitness"} in events
