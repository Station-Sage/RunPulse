"""P6 — 판단 등급 분류(위험 가드·교차 검토·결정 보고서)와 loop 설계 단계 연동."""
import json

import pytest

from scripts.audit import loop, triage

F = {"perspective": "ux", "kind": "tap", "verdict": "real", "impact": "버튼 작음", "fix": "키움"}
DESIGN = {"grade": "auto", "summary": "패딩 확대", "scope": ["frontend/src/a.svelte"], "verify": ["true"],
          "options": [{"name": "패딩", "pros": "간단", "cons": "없음"}], "recommendation": "패딩", "reason": "국소"}


@pytest.fixture(autouse=True)
def _no_opus(monkeypatch):
    from scripts.audit import budget
    monkeypatch.setattr(budget, "opus_allowed", lambda *a, **k: (False, "test"))


def _ask(design, verdict="agree"):
    calls = []

    def ask(prompt, model):
        calls.append(model)
        return json.dumps(design if "설계자" in prompt else {"verdict": verdict, "reason": "ok"})
    ask.calls = calls
    return ask


def test_parse_design_and_check_conservative():
    assert triage.parse_design("garbage")["grade"] == "user"
    assert triage.parse_design('{"grade":"auto","scope":"x"}')["scope"] == []
    assert triage.parse_check("???")["verdict"] == "unsure"


def test_risk_keyword_forces_user_without_calling_models():
    a = _ask(DESIGN)
    d = triage.decide({**F, "fix": "스키마 변경"}, ask_fn=a)
    assert d["tier"] == "user" and not a.calls


def test_auto_requires_cross_review_with_other_model():
    a = _ask(DESIGN)
    d = triage.decide(F, author="sonnet", ask_fn=a)
    assert d["tier"] == "auto" and a.calls == ["sonnet", "haiku"]


def test_disagree_or_bad_scope_or_missing_verify_is_user():
    assert triage.decide(F, ask_fn=_ask(DESIGN, "disagree"))["tier"] == "user"
    assert triage.decide(F, ask_fn=_ask({**DESIGN, "scope": ["src/db.py"]}))["tier"] == "user"
    assert triage.decide(F, ask_fn=_ask({**DESIGN, "verify": []}))["tier"] == "user"
    assert triage.decide(F, ask_fn=_ask({**DESIGN, "grade": "user"}))["tier"] == "user"


def test_report_has_options_and_reason():
    d = {"why": "사람 필요", "design": DESIGN}
    r = triage.report(F, d)
    assert "장점: 간단" in r and "추천: 패딩" in r and "사람 필요" in r


def test_design_phase_splits_auto_and_user(tmp_path, monkeypatch):
    monkeypatch.setattr(loop.notify, "send", lambda t: True)
    monkeypatch.setattr(loop.pacing, "check", lambda n: type("P", (), {"allowed": True, "reason": ""})())
    monkeypatch.setattr(loop, "PENDING_PATH", tmp_path / "pending.md")
    monkeypatch.setattr(loop, "agents_confirmed", lambda: [F, {**F, "kind": "other"}])
    p = tmp_path / "B.md"
    p.write_text("", encoding="utf-8")
    seq = iter([{"tier": "auto", "why": "ok", "design": DESIGN}, {"tier": "user", "why": "판단", "design": DESIGN}])
    st = {**loop._INIT, "phase": "design"}
    loop.step(st, path=p, act={"decide": lambda f: next(seq)})
    from scripts.autopilot import queue
    its = queue.parse(p)
    assert [i.stage for i in its] == ["queued", "blocked"] and its[0].scope == DESIGN["scope"]
    assert st["phase"] == "develop" and "판단" in (tmp_path / "pending.md").read_text(encoding="utf-8")


BIG = {**DESIGN, "scope": [f"frontend/src/lib/components/c{i}.svelte" for i in range(4)]}


def test_is_large():
    assert not triage.is_large(DESIGN)
    assert triage.is_large(BIG)
    assert triage.is_large({**DESIGN, "grade": "user"})
    assert triage.is_large({**DESIGN, "scope": ["frontend/src/routes/a/x.svelte", "frontend/src/routes/b/y.svelte"]})


def test_large_design_escalates_to_opus_with_sonnet_reviewer():
    a = _ask(BIG)
    d = triage.decide(F, ask_fn=a, opus_ok=lambda: True)
    assert d["author"] == "opus" and a.calls == ["sonnet", "opus", "sonnet"]


def test_large_design_stays_sonnet_when_opus_not_allowed():
    a = _ask(BIG)
    d = triage.decide(F, ask_fn=a, opus_ok=lambda: False)
    assert d["author"] == "sonnet" and "opus" not in a.calls


def test_open_unit_covering_kind_suppresses_duplicate_finding(tmp_path, monkeypatch):
    monkeypatch.setattr(loop, "PENDING_PATH", tmp_path / "pending.md")
    p = tmp_path / "B.md"
    p.write_text('- **[AUD-aaaaaa-1]** (커버: no-h1, other) 단위\n  <!-- autopilot: {"stage": "queued", "mode": "auto", "attempts": 0, "deps": [], "kind": "code"} -->\n', encoding="utf-8")
    f = {**F, "kind": "no-h1", "perspective": "ux", "verdict": "real"}
    called = []
    new = loop.propose([f], p, lambda x: called.append(x) or {"tier": "user", "why": "", "design": {}})
    assert new == [] and called == []


def test_design_prompt_asks_for_root_cause_and_recommendation():
    assert "근본원인" in triage._DESIGN and "추천안 하나" in triage._DESIGN
