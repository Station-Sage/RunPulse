"""훈련 방식 AI 추천 — 후보 가드·검증 게이트·폴백·캐시·게이트·요청 스레드 비차단."""
import json
import sqlite3
from datetime import date

import pytest

from src.services import method_recommend as mr

INP = {"goal": {"distance": "10K", "weeks_to_race": 12}, "run_days_per_week": 4,
       "history": {"avg_km_8w": 30}, "current": "balanced",
       "candidates": [{"id": "balanced"}, {"id": "threshold_vo2"}, {"id": "first_run3"}]}


def _out(**kw):
    d = {"recommended": "threshold_vo2", "ranking": ["threshold_vo2", "balanced"],
         "reasons": {"threshold_vo2": "최근 8주 평균 30km 로 강도 훈련을 소화할 수 있어요."}, "warnings": {}}
    d.update(kw)
    return json.dumps(d, ensure_ascii=False)


def test_validate_ok_completes_ranking():
    v = mr.validate(INP, "```json\n" + _out() + "\n```")
    assert v["recommended"] == "threshold_vo2"
    assert v["ranking"] == ["threshold_vo2", "balanced", "first_run3"]


@pytest.mark.parametrize("out", [
    None, "not json", _out(recommended="hansons"), _out(ranking=["threshold_vo2", "hansons"]),
    _out(reasons={}), _out(reasons={"hansons": "x"}),
    _out(reasons={"threshold_vo2": "주당 99km 를 달려야 해요."}),
    _out(reasons={"threshold_vo2": "무릎 통증이 있어도 괜찮아요."}),
    _out(reasons={"threshold_vo2": "**굵게**"}),
    _out(reasons={"threshold_vo2": "가" * 200}),
])
def test_validate_rejects(out):
    assert mr.validate(INP, out) is None


def test_fallback_in_candidates():
    assert mr.fallback(INP)["recommended"] == "first_run3" or INP["run_days_per_week"] > 3
    assert mr.fallback(INP)["recommended"] == "balanced"
    low = {**INP, "run_days_per_week": 3}
    f = mr.fallback(low)
    assert f["recommended"] == "first_run3" and f["ranking"][0] == "first_run3" and len(f["ranking"]) == 3
    only = {**INP, "candidates": [{"id": "x"}]}
    assert mr.fallback(only)["recommended"] == "x"


def test_hash_stable_and_sensitive():
    assert mr.src_hash(INP) == mr.src_hash(json.loads(json.dumps(INP)))
    assert mr.src_hash(INP) != mr.src_hash({**INP, "run_days_per_week": 5})


def _db():
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE ai_outputs (kind TEXT NOT NULL, scope_key TEXT NOT NULL, src_hash TEXT NOT NULL,"
              " body_json TEXT NOT NULL, job_id INTEGER, created_at TEXT NOT NULL, PRIMARY KEY (kind, scope_key))")
    return c


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setattr(mr, "build_input", lambda conn, today=None: INP)
    monkeypatch.setattr("src.training.goals.get_active_goal", lambda conn: {"id": 7})
    monkeypatch.setattr(mr, "_consent_ok", lambda conn: True)
    monkeypatch.setattr("src.ai.llm_budget.global_ratio", lambda: 0.0)
    monkeypatch.setattr("src.ai.llm_budget.limits", lambda: {"warm_stop_ratio": 0.9})
    monkeypatch.setattr("src.ai.provider_claude_queue.available", lambda conn, cfg: True)
    calls = []
    def fake(conn, cfg, **kw):
        calls.append(kw)
        return _out()
    monkeypatch.setattr("src.ai.provider_claude_queue.try_complete", fake)
    return calls


def test_generate_stores_then_cache_hit(env):
    c = _db()
    assert mr.generate(c, {})["recommended"] == "threshold_vo2"
    assert len(env) == 1 and env[0]["kind"] == "plan_draft"
    assert mr.generate(c, {})["recommended"] == "threshold_vo2"
    assert len(env) == 1
    v = mr.view(c)
    assert v["source"] == "ai" and v["current"] == "balanced"


def test_input_change_invalidates_cache(env, monkeypatch):
    c = _db()
    mr.generate(c, {})
    monkeypatch.setattr(mr, "build_input", lambda conn, today=None: {**INP, "run_days_per_week": 6})
    assert mr.get_cached(c, 7, {**INP, "run_days_per_week": 6}) is None
    assert mr.view(c)["source"] == "rule"


def test_no_consent_no_call_and_hidden(env, monkeypatch):
    c = _db()
    mr.generate(c, {})
    monkeypatch.setattr(mr, "_consent_ok", lambda conn: False)
    assert mr.view(c)["source"] == "rule"
    c.execute("DELETE FROM ai_outputs")
    env.clear()
    assert mr.generate(c, {}) is None and env == []


def test_budget_or_queue_off_no_call(env, monkeypatch):
    c = _db()
    monkeypatch.setattr("src.ai.provider_claude_queue.available", lambda conn, cfg: False)
    assert mr.generate(c, {}) is None
    monkeypatch.setattr("src.ai.provider_claude_queue.available", lambda conn, cfg: True)
    monkeypatch.setattr("src.ai.llm_budget.global_ratio", lambda: 0.95)
    assert mr.generate(c, {}) is None and env == []


def test_bad_ai_output_not_stored(env, monkeypatch):
    c = _db()
    monkeypatch.setattr("src.ai.provider_claude_queue.try_complete", lambda *a, **k: _out(recommended="hansons"))
    assert mr.generate(c, {}) is None
    assert c.execute("SELECT count(*) FROM ai_outputs").fetchone()[0] == 0


def test_warm_cooldown(monkeypatch):
    started = []
    monkeypatch.setattr(mr, "generate", lambda c, cfg: started.append(1))
    mr._cooldown.clear()
    assert mr.warm_in_background(":memory:", {}, now=1000.0) is True
    assert mr.warm_in_background(":memory:", {}, now=1100.0) is False
    assert mr.warm_in_background(":memory:", {}, now=1000.0 + mr.COOLDOWN_SEC + 1) is True


def test_build_input_and_view_on_real_db(monkeypatch):
    from datetime import timedelta

    from src.training.goals import add_goal
    from tests.helpers_pred import mem_conn, with_days
    today = date.today()
    conn = with_days(mem_conn())
    assert mr.build_input(conn, today) is None and mr.view(conn, today) is None
    gid = add_goal(conn, "g", 10.0, (today + timedelta(weeks=12)).isoformat(), None, rules_version=2)
    conn.execute("UPDATE goals SET distance_label='10k' WHERE id=?", (gid,))
    conn.commit()
    inp = mr.build_input(conn, today)
    assert inp["goal"]["weeks_to_race"] == 12 and len(inp["history"]["weekly_km_26w"]) == mr.HISTORY_WEEKS
    assert [c["id"] for c in inp["candidates"]] == ["balanced", "gundalf_10k_base", "threshold_vo2", "first_run3"]
    assert "health" not in json.dumps(inp)
    monkeypatch.setattr(mr, "_consent_ok", lambda c: False)
    v = mr.view(conn, today)
    assert v["source"] == "rule" and v["recommended"] == "balanced"
