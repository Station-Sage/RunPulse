"""C1 — 결정 소비(chosen→queued, redo→재제안·상한)."""
from scripts.audit import consume, decisions
from scripts.autopilot import queue

D = {"why": "교차 검토 disagree", "design": {"summary": "s", "recommendation": "A", "scope": ["tests/x.py"], "verify": ["pytest"],
     "options": [{"name": "x", "pros": "p", "cons": "c"}, {"name": "y"}]}}
F = {"kind": "tap", "impact": "i", "fix": "f"}


def _setup(tmp_path, stage="needs_decision"):
    q = tmp_path / "B.md"
    q.write_text(f'- **[AUD-1]** 제목\n  <!-- autopilot: {{"stage":"{stage}","mode":"auto","attempts":0,"deps":[]}} -->\n')
    dp = tmp_path / "d.json"
    decisions.append([decisions.build("AUD-1", F, D)], dp)
    return q, dp


def test_chosen_promotes_to_queued(tmp_path):
    q, dp = _setup(tmp_path)
    decisions.choose("AUD-1", "A", dp)
    out = consume.apply(q, lambda f: {}, dp)
    it = queue.parse(q)[0]
    assert it.stage == "queued" and it.scope == ["tests/x.py"] and out
    assert decisions.load(dp)[0]["status"] == "applied"
    assert consume.apply(q, lambda f: {}, dp) == []


def test_chosen_when_not_needs_decision_only_closes(tmp_path):
    q, dp = _setup(tmp_path, stage="done")
    decisions.choose("AUD-1", "A", dp)
    assert consume.apply(q, lambda f: {}, dp) == []
    assert decisions.load(dp)[0]["status"] == "applied" and queue.parse(q)[0].stage == "done"


def test_redo_requests_new_proposal_then_hits_limit(tmp_path):
    q, dp = _setup(tmp_path)
    seen = []

    def decide(f):
        seen.append(f["fix"])
        return {"why": "새 제안", "design": {"summary": f"s{len(seen)}", "options": [{"name": "z"}], "recommendation": "A"}}

    for n in (2, 3):
        decisions.choose("AUD-1", "redo", dp)
        consume.apply(q, decide, dp)
        r = decisions.load(dp)[0]
        assert r["status"] == "open" and r["rounds"] == n and r["summary"] == f"s{n-1}"
    assert "거절" in seen[0]
    decisions.choose("AUD-1", "redo", dp)
    consume.apply(q, decide, dp)
    r = decisions.load(dp)[0]
    assert r["status"] == "open" and "소진" in r["why"]
    assert len(seen) == 2
