import subprocess
from scripts.autopilot import queue, size_followup


def test_oversize_becomes_followup(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path)
    (tmp_path / "frontend/src").mkdir(parents=True)
    (tmp_path / "frontend/src/Big.svelte").write_text("x\n" * 310)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path)
    q = tmp_path / "BACKLOG.md"
    q.write_text("- **[A-1]** t\n  <!-- autopilot: {\"stage\": \"review\", \"mode\": \"auto\", \"attempts\": 0, \"deps\": []} -->\n")
    item = queue.QueueItem(item_id="A-1", text="t", kind="code", scope=["frontend/src/"])
    assert len(size_followup.append_followups(item, tmp_path, q)) == 1
    assert size_followup.append_followups(item, tmp_path, q) == []
    assert any(i.item_id.startswith("SPLIT-") and i.stage == "queued" for i in queue.parse(q))
