"""능동 인사이트 다듬기 근거(insight_evidence) + facts 포함 큐 다듬기(ADR-059 2단계)."""
from __future__ import annotations

import json
import sqlite3

import pytest

from src.ai import provider_claude_queue as pcq
from src.db_setup import create_tables
from src.services import insight_evidence as ev
from src.services import insight_polish as P
from src.services import insight_service as S

DAY = "2026-11-18"
RECOVERY = "회복 신호가 여러 개 낮아요. 오늘은 쉬어 가는 쪽을 권해요."
SIGNALS = [{"signal": "crs", "value": 1, "as_of": DAY, "freshness": "fresh"},
           {"signal": "checkin_fatigue", "value": 8, "as_of": DAY, "freshness": "fresh"}]


def _conn(consent: str | None = "claude_queue"):
    c = sqlite3.connect(":memory:")
    create_tables(c)
    if consent:
        c.execute("INSERT OR REPLACE INTO coach_consent(id, provider, accepted_at, exclude_notes, tools_enabled,"
                  " fallback_enabled) VALUES (1, ?, 't', 1, 0, 0)", (consent,))
    for name, v in (("tsb", -18.4), ("utrs", 38.0), ("acwr", 1.21)):
        c.execute("INSERT INTO metric_store(scope_type, scope_id, metric_name, provider, numeric_value, is_primary)"
                  " VALUES ('daily', ?, ?, 'runpulse:formula_v1', ?, 1)", (DAY, name, v))
    c.execute("INSERT INTO insight_events(kind,severity,as_of,dedupe_key,signals_json,text) VALUES"
              " ('recovery_low','watch',?,'recovery_low:global',?,?)", (DAY, json.dumps(SIGNALS), RECOVERY))
    c.execute("INSERT INTO insight_events(kind,severity,as_of,dedupe_key,signals_json,text) VALUES"
              " ('pain_flag','act',?,'pain_flag:global',?, '몸 상태 이상 신호가 있어요. 무리하지 말고 오늘 세션을 확인하세요.')",
              (DAY, json.dumps([{"signal": "injury", "value": 2}])))
    c.commit()
    return c


@pytest.fixture
def queue(monkeypatch):
    state = {"reply": None, "calls": []}
    monkeypatch.setattr(pcq, "available", lambda *a, **k: True)

    def fake(conn, config, **kw):
        state["calls"].append(kw)
        return state["reply"]
    monkeypatch.setattr(pcq, "try_complete", fake)
    return state


def test_evidence_facts_non_health_only():
    c = _conn()
    f = ev.evidence_facts(c, "recovery_low", SIGNALS, DAY)
    assert f == {"crs_level": 1, "crs_gate": "이지런만", "fatigue_checkin": 8, "tsb": -18.4, "utrs": 38.0, "acwr": 1.21}
    assert ev.evidence_facts(c, "pain_flag", [{"signal": "injury", "value": 2}], DAY) == {}
    assert ev.evidence_facts(c, "data_gap", [{"signal": "sync_garmin", "value": 4}], DAY) == {"sync_gap_days": 4}


def test_polish_key_changes_with_facts():
    assert ev.polish_key("a", {}) == "a"
    assert ev.polish_key("a", {"x": 1}) != ev.polish_key("a", {"x": 2})


def test_queue_polish_with_facts_hit_then_invalidated(queue):
    c = _conn()
    queue["reply"] = json.dumps([{"id": "1", "text": "회복 게이트가 이지런만이고 피로 체크인 8, 준비도 38이에요. 오늘은 쉬어 가요."}],
                                ensure_ascii=False)
    assert P.polish_open_events(c, {}) == 1
    prompt = queue["calls"][0]["prompt"]
    assert '"fatigue_checkin": 8' in prompt and "injury" not in prompt
    e = next(x for x in S.list_events(c) if x["kind"] == "recovery_low")
    assert e["source"] == "ai" and e["polished"] and "38" in e["text"]
    # 근거 지표가 바뀌면 키가 달라져 규칙 문장으로
    c.execute("UPDATE metric_store SET numeric_value=45 WHERE metric_name='utrs'")
    e = next(x for x in S.list_events(c) if x["kind"] == "recovery_low")
    assert e["source"] == "rule" and e["text"] == RECOVERY


def test_queue_polish_rejects_numbers_outside_facts_and_health(queue):
    c = _conn()
    queue["reply"] = json.dumps([{"id": "1", "text": "준비도 12점이에요."},
                                 {"id": "2", "text": "부상이 있어요. 쉬어요."}], ensure_ascii=False)
    assert P.polish_open_events(c, {}) == 0
    assert all(e["source"] == "rule" for e in S.list_events(c))


def test_no_consent_never_calls_queue(queue):
    c = _conn(consent=None)
    assert P.polish_open_events(c, {}) == 0
    assert queue["calls"] == []


def test_consent_revoked_hides_fact_based_polish(queue):
    c = _conn()
    queue["reply"] = json.dumps([{"id": "1", "text": "피로 체크인 8이라 오늘은 쉬어 가요."}], ensure_ascii=False)
    P.polish_open_events(c, {})
    c.execute("DELETE FROM coach_consent")
    e = next(x for x in S.list_events(c) if x["kind"] == "recovery_low")
    assert e["source"] == "rule"


def test_key_chain_skipped_for_fact_rows(monkeypatch):
    """큐 불가 + 근거 있음 → 키 기반 체인(facts 미전달)을 부르지 않는다(키 불일치로 매 동기화 재호출 방지)."""
    c = _conn()
    monkeypatch.setattr(pcq, "available", lambda *a, **k: False)
    monkeypatch.setattr(P, "polish_text", lambda *a, **k: pytest.fail("called"))
    rows = P.pending(c)
    assert any(r[2] for r in rows)
    # pain_flag(근거 없음)만 키 기반 경로 대상 — polish_text 대신 caller 로 확인
    monkeypatch.undo()
    monkeypatch.setattr(pcq, "available", lambda *a, **k: False)
    assert P.polish_open_events(c, None, caller=lambda p: "몸 상태 이상 신호가 있어요. 오늘 세션을 먼저 확인해요.") == 1
