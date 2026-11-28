import json
import subprocess

from scripts.audit import agents, consume, decisions
from scripts.autopilot import card_review, queue, size_followup
from scripts.console import server

GOOD = json.dumps({"review": "책임이 둘로 갈린다", "options": {"A": "경계가 명확", "B": "지금은 안정"}, "recommendation": "A",
                   "recommend_why": "함수군이 독립적", "split_plan": "parse* 를 parse_part.py 로 이동"})


def _card(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path)
    (tmp_path / "frontend/src").mkdir(parents=True)
    (tmp_path / "frontend/src/Big.svelte").write_text("x\n" * 310)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path)
    q = tmp_path / "BACKLOG.md"
    q.write_text("- **[A-1]** t\n  <!-- autopilot: {\"stage\": \"review\", \"mode\": \"auto\", \"attempts\": 0, \"deps\": []} -->\n")
    item = queue.QueueItem(item_id="A-1", text="t", kind="code", scope=["frontend/src/"])
    dp = tmp_path / "d.json"
    size_followup.append_followups(item, tmp_path, q, dp)
    return q, dp, decisions.load(dp)[0]


def test_parse_rejects_bad_output():
    assert card_review.parse("not json", ["A", "B"]) is None
    assert card_review.parse(GOOD.replace('"A", "recommend_why"', '"Z", "recommend_why"'), ["A", "B"]) is None
    assert card_review.parse("앞말 " + GOOD + " 뒷말", ["A", "B"])["recommendation"] == "A"


def test_review_success_fallback_and_pacing(tmp_path):
    _, _, rec = _card(tmp_path)
    assert rec["path"] == "frontend/src/Big.svelte"
    ok = json.loads(json.dumps(rec))
    assert card_review.review(ok, ask=lambda *a: GOOD)["source"] == "agent"
    assert ok["review_source"] == "agent" and ok["split_plan"] and ok["options"][0]["review"] == "경계가 명확"
    bad = json.loads(json.dumps(rec))
    for _ in range(card_review.MAX_TRIES - 1):
        assert card_review.review(bad, ask=lambda *a: "")["source"] == "pending" and "review_source" not in bad
    assert card_review.review(bad, ask=lambda *a: "")["source"] == "rule"
    assert bad["recommendation"] == rec["recommendation"]

    def hold(*a):
        raise agents.PacingHold("limit")
    wait = json.loads(json.dumps(rec))
    assert card_review.review(wait, ask=hold)["source"] == "pending" and "review_source" not in wait


def test_review_card_caches_and_split_plan_reaches_scope(tmp_path):
    q, dp, rec = _card(tmp_path)
    calls = []
    server.review_card(rec["id"], dp, ask=lambda *a: calls.append(1) or GOOD)
    assert server.review_card(rec["id"], dp, ask=lambda *a: calls.append(1) or GOOD)["source"] == "agent"
    assert len(calls) == 1
    assert server.review_card("nope", dp)["ok"] is False
    decisions.choose(rec["id"], "A", dp)
    consume.apply(q, lambda f: {}, dp)
    it = next(i for i in queue.parse(q) if i.item_id == rec["id"])
    assert any("parse_part.py" in s for s in it.scope)


def test_legacy_split_card_without_path(tmp_path):
    _, _, rec = _card(tmp_path)
    rec.pop("path"); rec.pop("lines")
    seen = []
    card_review.review(rec, ask=lambda p, *a: seen.append(p) or GOOD)
    assert "frontend/src/Big.svelte 파일(310줄)" in seen[0] and rec["review_source"] == "agent"
