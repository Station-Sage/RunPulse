"""지표 해석 AI 다듬기 표면(metric_interpretation, ADR-059 2단계) — 규칙 기본값·캐시 적중/미스·해시 변경·익명화·폴백."""
from __future__ import annotations

import json
import sqlite3

import pytest

from src.ai import llm_budget
from src.ai import provider_claude_queue as pcq
from src.db_setup import create_tables
from src.services import ai_wording as aw
from src.services import metric_interpretation as mi
from src.services import wording_warm_hooks
from src.services.metrics_explain import get_metric_explain

DAY = "2026-04-01"


def upsert_metric(c, scope_type, scope_id, name, v):
    c.execute("DELETE FROM metric_store WHERE scope_type=? AND scope_id=? AND metric_name=?", (scope_type, scope_id, name))
    c.execute("INSERT INTO metric_store(scope_type, scope_id, metric_name, provider, numeric_value, is_primary)"
              " VALUES (?,?,?, 'runpulse:formula_v1', ?, 1)", (scope_type, scope_id, name, v))


def _conn(consent: str | None = "claude_queue"):
    c = sqlite3.connect(":memory:")
    create_tables(c)
    if consent:
        c.execute("INSERT OR REPLACE INTO coach_consent(id, provider, accepted_at, exclude_notes, tools_enabled,"
                  " fallback_enabled) VALUES (1, ?, 't', 1, 0, 0)", (consent,))
    for name, v in (("ctl", 42.3), ("atl", 55.8), ("tsb", -13.5), ("acwr", 1.32), ("utrs", 61.0)):
        upsert_metric(c, "daily", DAY, name, v)
    upsert_metric(c, "daily", "2026-03-04", "tsb", -2.0)
    c.execute("INSERT INTO race_calendar(name, race_date, distance_km, priority, status) VALUES"
              " ('무릎 아픈 날 대회', '2026-05-03', 21.0975, 'A', 'planned')")
    c.execute("INSERT INTO planned_workouts(date, workout_type, distance_km) VALUES (?, 'tempo', 10)", (DAY,))
    c.commit()
    return c


@pytest.fixture
def queue(monkeypatch):
    state = {"reply": None, "calls": []}
    monkeypatch.setattr(pcq, "available", lambda *a, **k: True)
    monkeypatch.setattr(llm_budget, "global_ratio", lambda: 0.0)

    def fake(conn, config, **kw):
        state["calls"].append(kw)
        r = state["reply"]
        return r(kw["prompt"]) if callable(r) else r
    monkeypatch.setattr(pcq, "try_complete", fake)
    return state


def _tsb(c):
    return get_metric_explain(c, "daily", DAY, "tsb")


def test_facts_connect_trend_other_metrics_race_and_plan():
    c = _conn()
    it = mi.build_item(c, _tsb(c))
    f = it.facts
    assert it.scope_key == f"tsb:{DAY}"
    assert f["value"] == -13.5 and f["value_28d_ago"] == -2.0
    assert f["acwr"] == 1.32 and f["ctl"] == 42.3 and "tsb" not in f
    assert f["race_distance"] == "하프" and f["days_to_race"] == 32
    assert f["planned_today"] and f["planned_km"] == 10
    # 대회 이름(자유 입력)은 facts 에 없다
    assert "무릎" not in json.dumps(f, ensure_ascii=False)


def test_rule_text_is_default_without_cache():
    c = _conn()
    ex = _tsb(c)
    interp = ex["meaning"]["interpretation"]
    assert interp["source"] == "rule" and interp["text"] == mi.rule_text(ex) == ex["meaning"]["so_what"]


def test_warm_hit_then_hash_change_falls_back(queue):
    c = _conn()
    queue["reply"] = lambda p: json.dumps([{"id": f"tsb:{DAY}", "text": "피로가 체력보다 높아 폼이 −13.5예요. "
                                            "ACWR 1.32 이고 하프까지 32일 남았으니 회복을 먼저 챙겨요."}], ensure_ascii=False)
    n = aw.warm(c, {}, mi.SURFACE, mi.collect(c, DAY))
    assert n >= 1
    interp = _tsb(c)["meaning"]["interpretation"]
    assert interp["source"] == "ai" and "32일" in interp["text"]
    # 근거(다른 지표)가 바뀌면 해시가 달라져 규칙 문구로
    upsert_metric(c, "daily", DAY, "acwr", 1.61)
    c.commit()
    assert _tsb(c)["meaning"]["interpretation"]["source"] == "rule"


def test_warm_rejects_invented_numbers_and_health_terms(queue):
    c = _conn()
    queue["reply"] = lambda p: json.dumps([{"id": f"tsb:{DAY}", "text": "폼이 −25 까지 떨어질 수 있어요."},
                                           {"id": f"ctl:{DAY}", "text": "무릎을 조심하세요."}], ensure_ascii=False)
    aw.warm(c, {}, mi.SURFACE, mi.collect(c, DAY))
    assert _tsb(c)["meaning"]["interpretation"]["source"] == "rule"
    assert get_metric_explain(c, "daily", DAY, "ctl")["meaning"].get("interpretation", {}).get("source") != "ai"


def test_no_consent_never_calls_queue(queue):
    c = _conn(consent=None)
    assert aw.warm(c, {}, mi.SURFACE, mi.collect(c, DAY)) == 0
    assert queue["calls"] == []


def test_prompt_redacts_health_and_omits_race_name(queue):
    c = _conn()
    queue["reply"] = "[]"
    aw.warm(c, {}, mi.SURFACE, mi.collect(c, DAY))
    prompt = queue["calls"][0]["prompt"]
    assert "무릎" not in prompt and "days_to_race" in prompt


def test_activity_scope_has_no_interpretation():
    c = _conn()
    assert mi.build_item(c, {"slug": "trimp", "scope": {"type": "activity", "id": "1"}}) is None


def test_after_sync_hook_swallows_errors(monkeypatch):
    monkeypatch.setattr(aw, "warm_in_background", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("x")))
    wording_warm_hooks.after_sync("/nonexistent.db", {}, DAY)   # 예외 없이 반환
