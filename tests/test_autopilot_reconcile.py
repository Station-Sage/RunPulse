"""review 항목 중 BASE_BRANCH 에 병합된 것만 done 으로 승격되는지."""
import subprocess

from scripts.autopilot import queue, reconcile


def _git(cwd, *a):
    subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True)


def test_promote_merged(tmp_path):
    _git(tmp_path, "init", "-b", "base")
    _git(tmp_path, "config", "user.email", "a@b.c")
    _git(tmp_path, "config", "user.name", "t")
    _git(tmp_path, "commit", "--allow-empty", "-m", "fix: x (AUD-aaa-1)")
    _git(tmp_path, "checkout", "-b", "other")
    _git(tmp_path, "commit", "--allow-empty", "-m", "fix: y (AUD-bbb-2)")
    q = tmp_path / "BACKLOG.md"
    meta = '{"stage": "review", "mode": "auto", "attempts": 1, "deps": [], "kind": "code"}'
    q.write_text("".join(f"- **[{i}]** t\n  <!-- autopilot: {meta} -->\n\n" for i in ("AUD-aaa-1", "AUD-bbb-2", "AUD-aaa-10")))
    assert reconcile.promote_merged(q, "base", tmp_path) == ["AUD-aaa-1"]
    st = {i.item_id: i.stage for i in queue.parse(q)}
    assert st == {"AUD-aaa-1": "done", "AUD-bbb-2": "review", "AUD-aaa-10": "review"}


def test_prune_pending(tmp_path):
    q = tmp_path / "BACKLOG.md"
    def meta(st): return f'{{"stage": "{st}", "mode": "auto", "attempts": 0, "deps": [], "kind": "code"}}'
    q.write_text("".join(f"- **[{i}]** t\n  <!-- autopilot: {meta(s)} -->\n\n" for i, s in (("A", "done"), ("B", "blocked"))))
    pend = tmp_path / "pending.md"
    pend.write_text("## A\n- 문제\n\n## B\n- 문제\n")
    assert reconcile.prune_pending(q, pend) == ["A"]
    assert pend.read_text() == "## B\n- 문제\n"
    assert "## A" in (tmp_path / "pending.resolved.md").read_text()
