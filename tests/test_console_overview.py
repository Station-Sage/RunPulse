"""C1 — 관제 콘솔 overview/decision_list."""
from scripts.audit import decisions
from scripts.console import overview

D = {"why": "w", "design": {"summary": "s", "options": [{"name": "x"}], "recommendation": "A"}}


def test_queue_summary(tmp_path):
    q = tmp_path / "B.md"
    q.write_text('- **[A-1]** t\n  <!-- autopilot: {"stage":"needs_decision","mode":"auto","attempts":0,"deps":[]} -->\n'
                 '- **[A-2]** u\n  <!-- autopilot: {"stage":"queued","mode":"auto","attempts":0,"deps":[]} -->\n')
    s = overview.queue_summary(q)
    assert s["total"] == 2 and s["by_stage"]["queued"] == 1 and s["next"] == "A-2"
    assert s["attention"][0]["id"] == "A-1"


def test_overview_and_decisions(tmp_path):
    q = tmp_path / "B.md"
    q.write_text("")
    dp = tmp_path / "d.json"
    decisions.append([decisions.build("AUD-1", {"kind": "k"}, D), decisions.build("AUD-2", {"kind": "k"}, D)], dp)
    decisions.choose("AUD-1", "A", dp)
    o = overview.overview(now=1000.0, state_path=tmp_path / "none.json", queue_path=q, entries=[], dpath=dp)
    assert o["decisions_open"] == 1 and o["state"]["phase"] == "audit" and o["budget"]["pacing_ok"]
    assert [d["id"] for d in overview.decision_list(dp)] == ["AUD-2", "AUD-1"]
