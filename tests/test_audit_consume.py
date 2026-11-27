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


def test_promote_saves_undo_and_reopen_queued(tmp_path):
    q, dp = _setup(tmp_path)
    decisions.choose("AUD-1", "A", dp)
    consume.apply(q, lambda f: {}, dp)
    rec = decisions.load(dp)[0]
    assert rec["undo"]["stage"] == "needs_decision"
    assert consume.reopen(rec, q) is None
    assert rec["status"] == "open" and "undo" not in rec
    assert queue.parse(q)[0].stage == "needs_decision"


def test_reopen_closed_already_done(tmp_path):
    q, dp = _setup(tmp_path)
    recs = decisions.load(dp)
    recs[0]["options"][0]["action"] = "already_done"
    decisions.save(recs, dp)
    decisions.choose("AUD-1", "A", dp)
    consume.apply(q, lambda f: {}, dp)
    assert queue.parse(q)[0].stage == "done"
    rec = decisions.load(dp)[0]
    assert consume.reopen(rec, q) is None
    assert queue.parse(q)[0].stage == "needs_decision"


def test_reopen_refused_when_progressed_or_no_undo(tmp_path):
    q, dp = _setup(tmp_path)
    decisions.choose("AUD-1", "A", dp)
    consume.apply(q, lambda f: {}, dp)
    rec = decisions.load(dp)[0]
    queue.update_item(q, "AUD-1", stage="review")
    assert "이미 진행됨" in consume.reopen(rec, q)
    rec.pop("undo")
    assert "되돌릴 수 없음" in consume.reopen(rec, q)


def test_prune_caps_applied_only():
    data = [{"id": f"a{i}", "status": "applied", "created": f"2026-01-{i + 1:02d}"} for i in range(5)]
    data += [{"id": "o", "status": "open", "created": "2025-01-01"}, {"id": "r", "status": "redo", "created": "2025-01-01"}]
    out = decisions.prune(data, keep=2)
    assert [r["id"] for r in out if r["status"] == "applied"] == ["a3", "a4"]
    assert {"o", "r"} <= {r["id"] for r in out}


def _dep_setup(tmp_path):
    from scripts.autopilot import fail_handling
    q = tmp_path / "B.md"
    q.write_text('- **[AUD-1]** 제목\n  <!-- autopilot: {"stage":"needs_decision","mode":"auto","attempts":2,"deps":[],"fail_kind":"env","fail_reason":"[env] x"} -->\n')
    dp = tmp_path / "d.json"
    decisions.append([fail_handling.build_dep_card("AUD-1", "npm", "vitest", "r", "t")], dp)
    decisions.choose("AUD-1", "A", dp)
    return q, dp


def test_install_dep_success_requeues(tmp_path, monkeypatch):
    from scripts.autopilot import dep_install
    monkeypatch.setattr(dep_install, "install", lambda eco, name: (True, "ok"))
    q, dp = _dep_setup(tmp_path)
    consume.apply(q, lambda f: {}, dp)
    it = queue.parse(q)[0]
    assert it.stage == "queued" and it.attempts == 0 and not it.fail_reason


def test_install_dep_failure_marks_failed(tmp_path, monkeypatch):
    from scripts.autopilot import dep_install
    monkeypatch.setattr(dep_install, "install", lambda eco, name: (False, "E404"))
    q, dp = _dep_setup(tmp_path)
    out = consume.apply(q, lambda f: {}, dp)
    it = queue.parse(q)[0]
    assert it.stage == "failed" and "E404" in it.fail_reason and out
