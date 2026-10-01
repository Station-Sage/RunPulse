"""chat_result — 엔진 상태·동의 게이트·체인 구성·예산 (30-coach-chat design §4.1·§4.3·§8)."""
from datetime import date

import httpx
import pytest

from src.ai import chat_engine
from src.ai import chat_engine_result as cer
from src.ai.chat_engine import chat, chat_result
from src.services import today_service

CFG = {"ai": {"provider": "gemini", "gemini_api_key": "k", "groq_api_key": "k2"}}
CONSENT = {"provider": "gemini", "exclude_notes": False, "tools_enabled": False, "fallback_enabled": True}


class _Resp:
    def __init__(self, status, text="답변"):
        self.status_code = status
        self._p = {"choices": [{"message": {"content": text}}]}

    def json(self):
        return self._p


@pytest.fixture
def calls(monkeypatch):
    log = []

    def _post(url, *a, **k):
        log.append(url)
        return _Resp(404) if "generativelanguage" in url else _Resp(200, "그록 답변")
    monkeypatch.setattr(httpx, "post", _post)
    return log


def test_404_on_selected_falls_to_second_provider(db_conn, calls):
    r = chat_result(db_conn, "안녕", CFG, consent=CONSENT, require_consent=True)
    assert r.engine.status == "ok" and r.engine.provider == "groq"
    assert r.engine.fallback_reason == "http_404"
    assert [a.reason for a in r.engine.attempts] == ["http_404", None]


def test_all_fail_gives_rule_fallback_with_reason(db_conn, monkeypatch):
    monkeypatch.setattr(httpx, "post", lambda *a, **k: _Resp(404))
    r = chat_result(db_conn, "안녕", CFG, consent=CONSENT, require_consent=True)
    assert r.engine.status == "fallback" and r.engine.fallback_reason == "http_404"
    assert r.engine.attempts[0].http_status == 404 and r.text


def test_no_external_call_before_consent(db_conn, calls):
    r = chat_result(db_conn, "안녕", CFG, consent=None, require_consent=True)
    assert calls == []
    assert r.engine.status == "rule_only" and r.engine.fallback_reason == "no_consent"


def test_consent_for_other_provider_requires_reconsent(db_conn, calls):
    other = {**CONSENT, "provider": "groq"}
    r = chat_result(db_conn, "안녕", CFG, consent=other, require_consent=True)
    assert calls == [] and r.engine.fallback_reason == "no_consent"


def test_fallback_disabled_uses_single_provider(db_conn, calls):
    r = chat_result(db_conn, "안녕", CFG, consent={**CONSENT, "fallback_enabled": False}, require_consent=True)
    assert len(calls) == 1 and "generativelanguage" in calls[0]
    assert r.engine.status == "fallback"


def test_rule_only_without_keys_and_rule_by_choice(db_conn, calls):
    r = chat_result(db_conn, "안녕", {"ai": {"provider": "gemini"}}, consent=CONSENT, require_consent=True)
    assert r.engine.status == "rule_only" and r.engine.fallback_reason == "no_key"
    r2 = chat_result(db_conn, "안녕", {"ai": {"provider": "rule", "gemini_api_key": "k"}}, require_consent=True)
    assert r2.engine.status == "rule_by_choice" and calls == []


def test_exclude_notes_keeps_memo_out_of_prompt(db_conn, monkeypatch):
    today_service.save_checkin(db_conn, fatigue=6, pain="mild", note="비밀메모XYZ", input_date=date.today().isoformat())
    seen = []

    def _post(url, headers=None, json=None, **k):
        seen.append(str(json))
        return _Resp(200, "ok")
    monkeypatch.setattr(httpx, "post", _post)
    r = chat_result(db_conn, "오늘 컨디션 어때?", CFG, consent={**CONSENT, "exclude_notes": True}, require_consent=True)
    assert r.engine.status == "ok" and "비밀메모XYZ" not in seen[0]
    assert all(s["item"] != "체크인 메모" for s in r.sent_scope)
    chat_result(db_conn, "오늘 컨디션 어때?", CFG, consent=CONSENT, require_consent=True)
    assert "비밀메모XYZ" in seen[1]


def test_budget_exhausted_stops_chain(db_conn, monkeypatch):
    monkeypatch.setattr(cer, "TOTAL_BUDGET", -1)
    monkeypatch.setattr(httpx, "post", lambda *a, **k: pytest.fail("호출되면 안 됨"))
    r = chat_result(db_conn, "안녕", CFG, consent=CONSENT, require_consent=True)
    assert r.engine.status == "fallback" and r.engine.attempts[0].reason == "timeout"
    assert len(r.engine.attempts) == 1


def test_legacy_chat_returns_tuple(db_conn, calls):
    text, prov = chat(db_conn, "안녕", CFG)
    assert (text, prov) == ("그록 답변", "groq")
    text, prov = chat(db_conn, "안녕", {})
    assert prov == "rule" and text


def test_rule_text_has_no_ai_coach_self_reference(db_conn):
    r = chat_result(db_conn, "안녕", {}, require_consent=True)
    assert "/settings" not in r.text and chat_engine is not None


def test_v2_chip_with_ai_uses_free_text_path_with_tools(db_conn, monkeypatch):
    seen = {}

    def _run(conn, prompt, config, chain, tools=False, **_hooks):
        seen["prompt"], seen["tools"] = prompt, tools
        return "AI 답", "gemini", [cer.Attempt("gemini", "m", True)]

    monkeypatch.setattr(chat_engine, "run_chain", _run)
    cfg = {"ai": {"provider": "gemini", "gemini_api_key": "k"}}
    r = chat_result(db_conn, "오늘 훈련 어떻게 할까요?", cfg, chip_id="today_advice")
    assert r.text == "AI 답" and seen["tools"] is True
    assert "오늘 훈련 어떻게 할까요?" in seen["prompt"]
