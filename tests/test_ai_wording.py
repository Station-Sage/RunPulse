"""규칙 문구 AI 다듬기 공통 계층(ai_wording, ADR-059)."""
import json
import sqlite3

import pytest

from src.ai import llm_budget
from src.ai import provider_claude_queue as pcq
from src.services import ai_wording as aw

S = aw.register(aw.Surface(name="test_reason", guide="- 오늘 훈련 조정 이유를 설명합니다.", max_chars=80))


def _conn(consent: str | None = "claude_queue"):
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE ai_outputs (kind TEXT, scope_key TEXT, src_hash TEXT, body_json TEXT, job_id INTEGER,"
              " created_at TEXT, PRIMARY KEY(kind, scope_key))")
    c.execute("CREATE TABLE coach_consent (id INTEGER PRIMARY KEY, provider TEXT, accepted_at TEXT,"
              " exclude_notes INTEGER, tools_enabled INTEGER, fallback_enabled INTEGER)")
    if consent:
        c.execute("INSERT INTO coach_consent VALUES (1, ?, 't', 1, 0, 0)", (consent,))
    return c


@pytest.fixture
def queue(monkeypatch):
    """큐 가용 + 응답 주입. calls 에 프롬프트가 쌓인다."""
    state = {"reply": None, "calls": []}
    monkeypatch.setattr(pcq, "available", lambda *a, **k: True)
    monkeypatch.setattr(llm_budget, "global_ratio", lambda: 0.0)

    def fake(conn, config, **kw):
        state["calls"].append(kw)
        r = state["reply"]
        return r(kw["prompt"]) if callable(r) else r
    monkeypatch.setattr(pcq, "try_complete", fake)
    return state


ITEM = aw.Item("2026-11-19", "ACWR 1.52로 높아 오늘은 이지로 바꿨어요.", {"acwr": 1.52, "planned": "tempo"})


@pytest.mark.parametrize("src,out,ok", [
    ("ACWR 1.52", "ACWR 1.5", True), ("ACWR 1.52", "ACWR 2", True), ("12.35km", "12km", True),
    ("12.0km", "12km", True), ("5회", "5회 중 3회", False), ("", "새 수치 없음", True), ("4:05", "4:05", True),
])
def test_numbers_ok(src, out, ok):
    assert aw.numbers_ok(src, out) is ok


def test_redact_health_text_sentence_level():
    t = "감기 기운이 있어요. 무릎 통증도 있어요. 오늘은 쉬어요."
    assert aw.redact_health_text(t) == f"{aw.GENERIC_HEALTH} 오늘은 쉬어요."
    assert aw.redact_health_text("부하가 높아요.") == "부하가 높아요."


@pytest.mark.parametrize("out,ok", [
    ("부하가 높아 오늘은 이지로 바꿨어요.", True), ("", False), (None, False), ("# 제목", False),
    ("무릎이 걱정돼요.", False), ("x" * 81, False), ("ACWR 1.9라서요.", False),
])
def test_validate(out, ok):
    assert (aw.validate(S, "ACWR 1.52", out) is not None) is ok


def test_present_rule_then_ai_then_stale(queue):
    c = _conn()
    assert aw.present(c, S, ITEM.scope_key, ITEM.rule_text, ITEM.facts) == {"text": ITEM.rule_text, "source": "rule"}
    queue["reply"] = json.dumps([{"id": "2026-11-19", "text": "최근 부하(ACWR 1.5)가 높아서 오늘은 이지로 가요."}])
    assert aw.warm(c, {}, S, [ITEM]) == 1
    assert aw.present(c, S, ITEM.scope_key, ITEM.rule_text, ITEM.facts)["source"] == "ai"
    # 규칙 문구나 근거가 바뀌면 낡은 캐시는 쓰지 않는다
    assert aw.present(c, S, ITEM.scope_key, ITEM.rule_text, {"acwr": 1.6})["source"] == "rule"
    # 이미 신선하면 다시 부르지 않는다
    assert aw.warm(c, {}, S, [ITEM]) == 0 and len(queue["calls"]) == 1


def test_warm_rejects_invalid_and_unchanged_is_not_ai(queue):
    c = _conn()
    other = aw.Item("k2", "오늘은 쉬어요.")
    queue["reply"] = json.dumps([{"id": "2026-11-19", "text": "ACWR 3.0이에요."}, {"id": "k2", "text": "오늘은 쉬어요."}])
    assert aw.warm(c, {}, S, [ITEM, other]) == 1
    assert aw.present(c, S, ITEM.scope_key, ITEM.rule_text, ITEM.facts)["source"] == "rule"
    assert aw.present(c, S, "k2", "오늘은 쉬어요.") == {"text": "오늘은 쉬어요.", "source": "rule"}
    assert aw.warm(c, {}, S, [other]) == 0 and len(queue["calls"]) == 1   # 원문 유지도 재요청 안 함


def test_id_numbers_are_not_evidence(queue):
    c = _conn()
    queue["reply"] = json.dumps([{"id": "2026-11-19", "text": "19일은 부하가 높아 이지로 바꿨어요."}])
    assert aw.warm(c, {}, S, [ITEM]) == 0
    assert aw.get_cached(c, S, ITEM.scope_key, ITEM.rule_text, ITEM.facts) is None


def test_health_is_redacted_before_prompt(queue):
    c = _conn()
    queue["reply"] = "[]"
    aw.warm(c, {}, S, [aw.Item("h", "무릎 통증 기록이 있어요. 오늘은 쉬어요.", {"note": "감기"})])
    p = queue["calls"][0]["prompt"]
    assert "무릎" not in p and "감기" not in p and aw.GENERIC_HEALTH in p
    assert queue["calls"][0]["kind"] == "insight_polish" and queue["calls"][0]["model"] == "haiku"


@pytest.mark.parametrize("consent", [None])
def test_gate_requires_consent(queue, consent):
    c = _conn(consent)
    assert aw.gate(c, {}, S) == "no_consent"
    assert aw.warm(c, {}, S, [ITEM]) == 0 and not queue["calls"]


def test_gate_static_surface_skips_consent_but_not_budget(queue, monkeypatch):
    static = aw.register(aw.Surface(name="test_static", guide="-", needs_consent=False))
    assert aw.gate(_conn(None), {}, static) is None
    monkeypatch.setattr(llm_budget, "global_ratio", lambda: 0.95)
    assert aw.gate(_conn(None), {}, static) == "capped"
    monkeypatch.setattr(llm_budget, "global_ratio", lambda: 0.0)
    monkeypatch.setattr(pcq, "available", lambda *a, **k: False)
    assert aw.gate(_conn(None), {}, static) == "unavailable"


def test_register_conflict_and_missing_template():
    with pytest.raises(ValueError):
        aw.register(aw.Surface(name="test_reason", guide="다른 지침"))
    with pytest.raises(ValueError):
        aw.register(aw.Surface(name="test_x", guide="-", template="nope.txt"))
    assert aw.get_surface("test_reason") is S


def test_get_cached_without_table_is_none():
    assert aw.get_cached(sqlite3.connect(":memory:"), S, "k", "x") is None
    assert aw.present(None, S, "k", "x") == {"text": "x", "source": "rule"}


def test_queue_failure_stores_nothing(queue):
    c = _conn()
    queue["reply"] = None
    assert aw.warm(c, {}, S, [ITEM]) == 0
    assert c.execute("SELECT COUNT(*) FROM ai_outputs").fetchone()[0] == 0


def test_consent_any_provider():
    from src.services import ai_wording as aw
    assert aw._consent_ok(_conn("gemini")) is True
    assert aw._consent_ok(_conn(None)) is False
