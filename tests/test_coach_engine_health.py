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
    assert h.engine_label("fallback", "rule", None, 0, "http_404") == "규칙 답변 (AI 연결 실패)"
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


def test_legacy_rule_label_single_source():
    assert h.engine_label("legacy_rule", "rule", None, 0, None) == "규칙 답변 (이전 방식)"
    assert h.engine_label("???", None, None, 0, None) == "답변 엔진 정보 없음"
    assert h.message_engine_view(None, None)["label"] == "규칙 답변 (이전 방식)"


def test_row_status_overrides_engine_json():
    v = h.message_engine_view(None, None, "error")
    assert v["status"] == "error" and "답변을 만들지 못했어요" in v["label"]
    ok_json = '{"status": "ok", "provider": "gemini", "model": "gemini-2.5-flash"}'
    assert h.message_engine_view(ok_json, "gemini", "cancelled")["label"] == "중단됨"
    assert h.message_engine_view(ok_json, "gemini", "done")["status"] == "ok"


def test_message_engine_view_lists_actual_attempts():
    """S4-87: '원인 보기'는 이 답변에서 실제로 시도한 provider 들을 순서대로(재시도 포함) 보여 준다."""
    import json
    eng = {"status": "fallback", "provider": "rule", "fallback_reason": "network", "attempts": [
        {"provider": "openai", "model": "gpt-4o-mini", "ok": False, "reason": "network", "latency_ms": 3},
        {"provider": "gemini", "model": "gemini-2.5-flash", "ok": False, "reason": "http_5xx", "http_status": 500},
        "broken"]}
    v = h.message_engine_view(json.dumps(eng), None, "done")
    assert v["attempts"] == [
        {"provider": "openai", "model": "gpt-4o-mini", "ok": False, "reason": "network"},
        {"provider": "gemini", "model": "gemini-2.5-flash", "ok": False, "reason": "http_5xx"}]
    assert h.attempt_views(None) == [] and h.attempt_views({"attempts": None}) == []


def test_failure_history_prefix_on_retry_success():
    """S4-88: 다른 provider 로 재시도해 성공하면 라벨에 실패 이력을 함께 쓴다(TXT-1 확정)."""
    import json
    eng = {"status": "ok", "provider": "groq", "model": "llama-3.3-70b", "fallback_reason": "http_429",
           "tool_calls": 2, "attempts": [
               {"provider": "gemini", "model": "gemini-2.5-flash", "ok": False, "reason": "http_429"},
               {"provider": "groq", "model": "llama-3.3-70b", "ok": True, "reason": None}]}
    v = h.message_engine_view(json.dumps(eng), None, "done")
    assert v["label"] == "Gemini 실패(사용량 한도) → Groq · llama-3.3-70b · 조회 2회"
    assert h.failure_history([{"provider": "x", "ok": False, "reason": "timeout"}]) == "x 실패(시간 초과) → "


def test_failure_history_absent_for_plain_and_legacy_messages():
    import json
    ok = {"status": "ok", "provider": "gemini", "model": "gemini-2.5-flash",
          "attempts": [{"provider": "gemini", "model": "gemini-2.5-flash", "ok": True}]}
    assert h.message_engine_view(json.dumps(ok), None, "done")["label"] == "Gemini 2.5 Flash"
    # attempts 없는 옛 메시지·ai_model 만 있는 더 옛 메시지는 그대로
    assert h.message_engine_view('{"status": "ok", "provider": "gemini"}', None)["label"] == "Gemini"
    assert h.message_engine_view(None, "groq")["label"] == "Groq"
    # 규칙 대체 라벨은 배너가 사유를 보여 주므로 접두를 붙이지 않는다
    fb = {"status": "fallback", "provider": "rule", "attempts": [{"provider": "gemini", "ok": False, "reason": "timeout"}]}
    assert h.message_engine_view(json.dumps(fb), None)["label"] == "규칙 답변 (AI 연결 실패)"
    assert h.failure_history(None) == "" and h.failure_history(["bad", {"ok": False}]) == ""


def test_every_status_reason_has_label():
    """S4-88: reason_for_status 가 만드는 코드(http_4xx 포함)는 모두 사람이 읽는 라벨이 있다."""
    from src.ai.provider_common import REASON_LABELS, reason_for_status
    for st in (400, 401, 403, 404, 413, 429, 500, 503):
        assert reason_for_status(st) in REASON_LABELS
    assert h.reason_label("http_4xx") == "요청 거부(4xx)"
