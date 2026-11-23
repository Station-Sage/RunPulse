"""Opus 게이트(budget)·ask 폴백·버전업 감사(release)·비전 프롬프트."""
import json

from scripts.audit import agents, budget, perspectives, release, review, triage
from scripts.audit.vision import VISION


def test_budget_call_cap(tmp_path):
    p = tmp_path / "c.json"
    assert budget.opus_allowed(entries=[], path=p)[0]
    for _ in range(budget.OPUS_CALLS_PER_WEEK):
        budget.record_call(path=p)
    ok, why = budget.opus_allowed(entries=[], path=p)
    assert not ok and "소진" in why


def test_ask_falls_back_to_sonnet_when_opus_blocked(monkeypatch):
    used = []
    monkeypatch.setattr(agents.budget, "opus_allowed", lambda *a, **k: (False, "x"))
    monkeypatch.setattr(agents.budget, "record_call", lambda *a, **k: used.append("rec"))
    seen = []
    monkeypatch.setattr(agents.subprocess, "run", lambda cmd, **k: seen.append(cmd) or type("R", (), {"returncode": 0, "stdout": "ok"})())
    agents.ask("p", "opus")
    assert "sonnet" in seen[0] and "opus" not in seen[0] and not used


def test_ask_records_opus_call(monkeypatch):
    used = []
    monkeypatch.setattr(agents.budget, "opus_allowed", lambda *a, **k: (True, ""))
    monkeypatch.setattr(agents.budget, "record_call", lambda *a, **k: used.append(1))
    monkeypatch.setattr(agents.subprocess, "run", lambda cmd, **k: type("R", (), {"returncode": 0, "stdout": "ok"})())
    agents.ask("p", "opus")
    assert used == [1]


def test_prompts_carry_vision_and_release_models_are_opus():
    assert "vision" in perspectives.AUDIT_MODELS
    assert set(perspectives.RELEASE_MODELS.values()) == {"opus"}
    assert VISION in perspectives.build_prompt("ux", {})
    assert VISION in review._PROMPT and VISION in triage._DESIGN and VISION in triage._CHECK


def _pkg(tmp_path, v):
    p = tmp_path / "package.json"
    p.write_text(json.dumps({"version": v}))
    return p


def test_release_due_and_run(tmp_path):
    pkg, st = _pkg(tmp_path, "0.1.0"), tmp_path / "st.json"
    assert release.due(pkg, st)
    assert not release.run(pkg, st, audit=lambda: {"ran": True}, allowed=lambda: (False, "한도"))["ran"]
    assert release.due(pkg, st)
    e = release.run(pkg, st, audit=lambda: {"ran": True, "outcome": "done"}, allowed=lambda: (True, ""))
    assert e["ran"] and not release.due(pkg, st)
    assert not release.run(pkg, st)["ran"]


def test_release_failed_audit_not_marked(tmp_path):
    pkg, st = _pkg(tmp_path, "0.2.0"), tmp_path / "st.json"
    release.run(pkg, st, audit=lambda: {"ran": True, "outcome": "sweep_failed"}, allowed=lambda: (True, ""))
    assert release.due(pkg, st)
