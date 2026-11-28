import subprocess
from scripts.audit import consume, decisions
from scripts.autopilot import queue, size_followup, split_card


def _setup(tmp_path, lines=310):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path)
    (tmp_path / "frontend/src").mkdir(parents=True)
    (tmp_path / "frontend/src/Big.svelte").write_text("x\n" * lines)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path)
    q = tmp_path / "BACKLOG.md"
    q.write_text("- **[A-1]** t\n  <!-- autopilot: {\"stage\": \"review\", \"mode\": \"auto\", \"attempts\": 0, \"deps\": []} -->\n")
    item = queue.QueueItem(item_id="A-1", text="t", kind="code", scope=["frontend/src/"])
    return item, q, tmp_path / "d.json"


def test_oversize_waits_for_decision(tmp_path):
    item, q, dp = _setup(tmp_path)
    assert len(size_followup.append_followups(item, tmp_path, q, dp)) == 1
    assert size_followup.append_followups(item, tmp_path, q, dp) == []
    it = next(i for i in queue.parse(q) if i.item_id.startswith("SPLIT-"))
    assert it.stage == "needs_decision"
    card = decisions.load(dp)[0]
    assert [o["action"] for o in card["options"]] == ["split", "deferred"] and card["recommend_why"]


def test_recommendation_by_overshoot():
    assert split_card.recommend(320)[0] == "deferred"
    assert split_card.recommend(500)[0] == "split"


def test_choose_split_queues_and_defer_closes(tmp_path):
    for key, stage, res in (("A", "queued", ""), ("B", "done", "deferred")):
        d = tmp_path / key
        d.mkdir()
        item, q, dp = _setup(d)
        size_followup.append_followups(item, d, q, dp)
        sid = next(i.item_id for i in queue.parse(q) if i.item_id.startswith("SPLIT-"))
        decisions.choose(sid, key, dp)
        consume.apply(q, lambda f: {}, dp)
        it = next(i for i in queue.parse(q) if i.item_id == sid)
        assert (it.stage, it.resolution) == (stage, res)
