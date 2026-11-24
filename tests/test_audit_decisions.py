"""A2 — 구조화 결정함(pending_decisions.json) build/append/choose."""
from scripts.audit import decisions

F = {"kind": "tap"}
D = {"why": "교차 검토 disagree", "design": {"summary": "s", "recommendation": "A",
     "options": [{"name": "x", "pros": "p", "cons": "c"}, {"name": "y"}]}}


def test_build_fields():
    r = decisions.build("AUD-1", F, D)
    assert r["status"] == "open" and [o["key"] for o in r["options"]] == ["A", "B"] and r["revert"]


def test_append_dedup_and_load(tmp_path):
    p = tmp_path / "d.json"
    r = decisions.build("AUD-1", F, D)
    decisions.append([r], p)
    decisions.append([r], p)
    assert len(decisions.load(p)) == 1
    assert decisions.load(tmp_path / "none.json") == []


def test_choose(tmp_path):
    p = tmp_path / "d.json"
    decisions.append([decisions.build("AUD-1", F, D)], p)
    assert decisions.choose("AUD-1", "A", p)["status"] == "chosen"
    assert decisions.choose("AUD-1", "redo", p)["status"] == "redo"
    assert decisions.choose("nope", "A", p) is None
