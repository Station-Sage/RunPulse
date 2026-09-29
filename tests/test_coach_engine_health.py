"""coach_engine_health / coach_consent — 엔진 라벨, H0 집계, 동의 upsert."""
from __future__ import annotations

import json

import pytest

from src.services import coach_consent, coach_engine_health as h


def _add(conn, status, reason=None, provider="rule", http=None, tool_calls=0):
    eng = {"status": status, "provider": provider, "model": "gemini-2.5-flash", "fallback_reason": reason,
           "tool_calls": tool_calls, "attempts": [{"provider": "gemini", "model": "gemini-2.5-flash",
                                                    "reason": reason, "http_status": http}]}
    conn.execute("INSERT INTO chat_messages (role, content, engine_json) VALUES ('assistant', 'x', ?)",
                 (json.dumps(eng),))
    conn.commit()


def test_labels():
    assert h.engine_label("ok", "gemini", "gemini-2.5-flash", 3, None) == "Gemini 2.5 Flash · 조회 3회"
    assert h.engine_label("fallback", "rule", None, 0, "http_404") == "기본 규칙 답변"
    assert h.engine_label("rule_only", "rule", None, 0, None) == "규칙 답변 (AI 미설정)"
    assert h.engine_label("rule_by_choice", "rule", None, 0, None) == "규칙 답변 (AI 끔)"
    assert "동의 필요" in h.engine_label("error", None, None, 0, "no_consent")
    assert h.engine_label("cancelled", None, None, 0, None) == "중단됨"


def test_health_degraded_after_three_fallbacks_and_clears_on_ok(db_conn):
    for _ in range(3):
        _add(db_conn, "fallback", "http_404", http=404)
    s = h.health_summary(db_conn)
    assert s["consecutive_failures"] == 3 and s["degraded"] is True
    assert s["last_error"]["status"] == 404 and s["last_error"]["reason"] == "http_404"
    _add(db_conn, "ok", provider="gemini")
    s = h.health_summary(db_conn)
    assert s["consecutive_failures"] == 0 and s["degraded"] is False and s["last_ok_at"]


def test_health_ignores_rule_only(db_conn):
    _add(db_conn, "fallback", "http_404", http=404)
    _add(db_conn, "rule_only")
    _add(db_conn, "fallback", "http_404", http=404)
    assert h.health_summary(db_conn)["consecutive_failures"] == 2


def test_save_consent_upsert_keeps_accepted_at_for_same_provider(db_conn):
    assert coach_consent.get_consent(db_conn) is None
    first = coach_consent.save_consent(db_conn, "gemini")
    db_conn.execute("UPDATE coach_consent SET accepted_at='2020-01-01 00:00:00'")
    second = coach_consent.save_consent(db_conn, "gemini", exclude_notes=True)
    assert second["accepted_at"] == "2020-01-01 00:00:00" and second["exclude_notes"] is True
    third = coach_consent.save_consent(db_conn, "groq")
    assert third["accepted_at"] != "2020-01-01 00:00:00"
    assert first["tools_enabled"] is True


def test_save_consent_rejects_non_llm(db_conn):
    with pytest.raises(ValueError):
        coach_consent.save_consent(db_conn, "rule")


def test_get_engine_rule_only_when_no_keys(db_conn):
    e = h.get_engine(db_conn, {"ai": {"provider": "gemini"}})
    assert e["mode"] == "rule_only" and e["chain"] == []
