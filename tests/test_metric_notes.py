"""지표 안내 문구 사전 생성(metric_notes) + ACWR 저부하·휴식기 밴드."""
import json
import sqlite3

from src.services import metric_notes as mn
from src.services.metric_display import action_hint, band_key
from src.ai import provider_claude_queue as pcq


def _conn():
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE ai_outputs (kind TEXT, scope_key TEXT, src_hash TEXT, body_json TEXT, job_id INTEGER,"
              " created_at TEXT, PRIMARY KEY(kind, scope_key))")
    return c


def test_band_key_acwr_low_and_layoff():
    assert band_key("acwr", "caution", 0.6) == "low"
    assert band_key("acwr", "caution", 0.1) == "layoff"
    assert band_key("acwr", "caution", 1.4) == "caution"
    assert band_key("cirs", "good", 0.1) == "good"


def test_action_hint_layoff_text_differs_from_overload():
    assert "휴식기" in action_hint("acwr", "caution", value=0.05)
    assert "줄이세요" in action_hint("acwr", "caution", value=1.4)


def test_cached_note_used_only_when_rule_unchanged():
    c = _conn()
    rule = action_hint("acwr", "caution", value=0.05)
    c.execute("INSERT INTO ai_outputs VALUES ('metric_note','acwr:layoff',?,?,NULL,'t')",
              (mn._hash(rule), json.dumps({"text": "쉬는 중이에요."})))
    assert action_hint("acwr", "caution", value=0.05, conn=c) == "쉬는 중이에요."
    c.execute("UPDATE ai_outputs SET src_hash='stale'")
    assert action_hint("acwr", "caution", value=0.05, conn=c) == rule


def test_warm_stores_valid_and_rejects_numbers(monkeypatch):
    c = _conn()
    monkeypatch.setattr(pcq, "available", lambda *a, **k: True)

    def fake(conn, config, **kw):
        return json.dumps([{"id": "acwr:layoff", "text": "쉬는 기간이에요. 천천히 복귀하세요."},
                           {"id": "acwr:low", "text": "부하가 70% 줄었어요."}])
    monkeypatch.setattr(pcq, "try_complete", fake)
    assert mn.warm(c, {}) == 1
    n = c.execute("SELECT scope_key FROM ai_outputs").fetchall()
    assert n == [("acwr:layoff",)]


def test_warm_noop_when_queue_unavailable(monkeypatch):
    monkeypatch.setattr(pcq, "available", lambda *a, **k: False)
    assert mn.warm(_conn(), {}) == 0
