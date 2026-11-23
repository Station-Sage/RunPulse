"""P5 — 필수 브라우저 스윕 가드, 독립 검토 게이트, 사이클 요약."""
import json
import subprocess
import time

from scripts.audit import cycle, review


def _cp(out, rc=0, err=""):
    return subprocess.CompletedProcess([], rc, out, err)


def test_browser_sweep_fails_on_zero_cells(monkeypatch):
    monkeypatch.setattr(cycle.shutil, "which", lambda n: "/usr/bin/node")
    monkeypatch.setattr(cycle.subprocess, "run", lambda *a, **k: _cp(json.dumps({"swept": 0, "failed": []}), 1))
    n, err = cycle.browser_sweep()
    assert n == 0 and err


def test_browser_sweep_ok_and_no_node(monkeypatch):
    monkeypatch.setattr(cycle.shutil, "which", lambda n: "/usr/bin/node")
    monkeypatch.setattr(cycle.subprocess, "run", lambda *a, **k: _cp("x\n" + json.dumps({"swept": 282, "failed": []})))
    assert cycle.browser_sweep() == (282, None)
    monkeypatch.setattr(cycle.shutil, "which", lambda n: None)
    assert cycle.browser_sweep()[1] == "node 없음"


def test_cycle_skips_agents_when_sweep_fails(tmp_path, monkeypatch):
    monkeypatch.setattr(cycle, "CYCLES_PATH", tmp_path / "c.jsonl")
    monkeypatch.setattr(cycle, "skip_reason", lambda n, f=False: None)
    monkeypatch.setattr(cycle.procs, "reap", lambda: [])
    monkeypatch.setattr(cycle, "browser_sweep", lambda limit=None: (0, "boom"))
    sent = []
    monkeypatch.setattr(cycle.notify, "send", lambda t: sent.append(t))
    monkeypatch.setattr(cycle.agents, "main", lambda a: (_ for _ in ()).throw(AssertionError("agents ran")))
    e = cycle.run_cycle()
    assert e["outcome"] == "sweep_failed" and sent and "boom" in sent[0]


def test_cycle_runs_agents_with_review_after_sweep(tmp_path, monkeypatch):
    monkeypatch.setattr(cycle, "CYCLES_PATH", tmp_path / "c.jsonl")
    monkeypatch.setattr(cycle, "skip_reason", lambda n, f=False: None)
    monkeypatch.setattr(cycle.procs, "reap", lambda: [])
    monkeypatch.setattr(cycle, "browser_sweep", lambda limit=None: (10, None))
    monkeypatch.setattr(cycle.agents, "group_issues", lambda l: {"k": [1]})
    seen = []
    monkeypatch.setattr(cycle.agents, "main", lambda a: seen.append(a) or 0)
    monkeypatch.setattr(cycle.agents, "FINDINGS_PATH", tmp_path / "none.json")
    monkeypatch.setattr(cycle.notify, "send", lambda t: None)
    e = cycle.run_cycle()
    assert e["outcome"] == "done" and "--review" in seen[0]
    assert "스윕 10셀" in cycle.summary(e)


def test_parse_verdict_and_confirmed():
    assert review.parse_verdict('x {"verdict":"confirm","reason":"ok"}')["verdict"] == "confirm"
    assert review.parse_verdict("garbage")["verdict"] == "unsure"
    assert review.parse_verdict('{"verdict":"bogus"}')["verdict"] == "unsure"
    fs = [{"verdict": "real", "review": {"verdict": "confirm"}}, {"verdict": "real", "review": {"verdict": "reject"}}]
    assert review.confirmed(fs) == fs[:1]


def test_review_uses_different_model_and_skips_non_real(monkeypatch):
    calls = []
    monkeypatch.setattr(review, "ask", lambda p, m: calls.append(m) or '{"verdict":"reject","reason":"synth"}')
    out = review.review([{"verdict": "real", "kind": "k", "perspective": "ux"},
                         {"verdict": "noise", "kind": "k2"}], {"k": [{"cell": "a|b|c", "note": "n"}]})
    assert calls == ["haiku"] and out[0]["review"]["verdict"] == "reject" and "review" not in out[1]
