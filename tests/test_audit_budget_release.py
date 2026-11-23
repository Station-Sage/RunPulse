"""Opus 게이트(budget)·ask 폴백·버전업 감사(release)·비전 프롬프트."""
import json

from scripts.audit import agents, budget, perspectives, release, review, triage
from scripts.audit.vision import VISION


def test_budget_utilization_caps():
    now = 1_000_000.0
    ob = lambda w, u: {"rate_limit": {"rateLimitType": w, "utilization": u, "resetsAt": now + 3600}}  # noqa: E731
    assert budget.opus_allowed(now, entries=[])[0]
    assert not budget.opus_allowed(now, entries=[ob("seven_day", 0.6)])[0]


def test_ask_falls_back_to_sonnet_when_opus_blocked(monkeypatch):
    monkeypatch.setattr(agents.budget, "opus_allowed", lambda *a, **k: (False, "x"))
    seen = []
    monkeypatch.setattr(agents.subprocess, "run", lambda cmd, **k: seen.append(cmd) or type("R", (), {"returncode": 0, "stdout": "ok"})())
    agents.ask("p", "opus")
    assert "sonnet" in seen[0] and "opus" not in seen[0]


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


def test_ask_records_rate_limit_and_pacing_blocks(monkeypatch, tmp_path):
    from scripts.audit import agents
    from scripts.autopilot import ledger, pacing, settings
    monkeypatch.setattr(settings, "STATE_DIR", tmp_path)
    monkeypatch.setattr(settings, "LEDGER_PATH", tmp_path / "ledger.jsonl")
    monkeypatch.setattr(agents.budget, "opus_allowed", lambda: (True, ""))
    out = ('{"type":"rate_limit_event","rate_limit_info":{"rateLimitType":"five_hour","utilization":0.95,'
           '"status":"allowed","resetsAt":%d}}\n{"type":"result","result":"hi","total_cost_usd":0.1}\n') % (
        __import__("time").time() + 3600)
    monkeypatch.setattr(agents.subprocess, "run",
                        lambda *a, **k: type("R", (), {"returncode": 0, "stdout": out})())
    assert agents.ask("p", "sonnet") == "hi"
    assert ledger.read_all()[-1]["rate_limit"]["utilization"] == 0.95
    import pytest
    with pytest.raises(agents.PacingHold):
        agents.ask("p", "sonnet")


def test_pacing_hold_until_file(monkeypatch, tmp_path):
    import time
    from scripts.autopilot import pacing, settings
    monkeypatch.setattr(settings, "STATE_DIR", tmp_path)
    (tmp_path / "hold_until").write_text(str(time.time() + 600))
    assert not pacing.check(entries=[]).allowed
