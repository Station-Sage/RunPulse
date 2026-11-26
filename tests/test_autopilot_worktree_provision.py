"""worktree.provision — 워크트리에 없는 untracked 의존성(.venv·node_modules)을 메인 체크아웃에서 링크."""
from __future__ import annotations

import subprocess

from scripts.autopilot import worktree


def _git_wt(tmp_path):
    wt = tmp_path / "wt"
    wt.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=wt, check=True)
    return wt


def _src(tmp_path):
    src = tmp_path / "main"
    for rel in worktree.PROVISION_PATHS:
        (src / rel).mkdir(parents=True)
    return src


def test_links_missing_paths_and_excludes(tmp_path):
    wt, src = _git_wt(tmp_path), _src(tmp_path)
    done = worktree.provision(wt, src)
    assert set(done) == set(worktree.PROVISION_PATHS)
    assert (wt / ".venv").is_symlink() and (wt / ".venv").resolve() == (src / ".venv").resolve()
    exclude = (wt / ".git" / "info" / "exclude").read_text()
    assert ".venv" in exclude.splitlines()
    assert subprocess.run(["git", "status", "--porcelain"], cwd=wt, capture_output=True, text=True).stdout.strip() == ""


def test_idempotent(tmp_path):
    wt, src = _git_wt(tmp_path), _src(tmp_path)
    worktree.provision(wt, src)
    assert worktree.provision(wt, src) == []


def test_replaces_broken_link(tmp_path):
    wt, src = _git_wt(tmp_path), _src(tmp_path)
    (wt / ".venv").symlink_to(tmp_path / "gone")
    assert ".venv" in worktree.provision(wt, src)
    assert (wt / ".venv").exists()


def test_skips_existing_real_dir_and_missing_source(tmp_path):
    wt, src = _git_wt(tmp_path), _src(tmp_path)
    (wt / ".venv").mkdir()
    (src / "frontend" / "node_modules").rmdir()
    done = worktree.provision(wt, src)
    assert ".venv" not in done and "frontend/node_modules" not in done


def test_noop_when_same_dir_or_missing_wt(tmp_path):
    src = _src(tmp_path)
    assert worktree.provision(src, src) == []
    assert worktree.provision(tmp_path / "nope", src) == []


def test_verify_env_normalizes_minimal_systemd_env(monkeypatch):
    from scripts.autopilot import settings
    env = worktree.verify_env({"PATH": "/usr/bin:/bin", "PYTHONPATH": "x", "NODE_OPTIONS": "--bad"})
    parts = env["PATH"].split(":")
    assert str(settings.PROJECT_ROOT / ".venv/bin") in parts
    assert parts.count("/usr/bin") == 1
    assert env["HOME"] and env["CI"] == "1"
    assert env["VIRTUAL_ENV"].endswith(".venv")
    assert "PYTHONPATH" not in env and "NODE_OPTIONS" not in env


def test_retry_prompt_includes_previous_verify_failure():
    from scripts.autopilot import prompts, queue
    it = queue.QueueItem(item_id="X-1", text="t", kind="code", attempts=1, fail_kind="verify", fail_reason="Could not find foo.test.mjs")
    assert "Could not find foo.test.mjs" in prompts.build_prompt(it)
    it.attempts = 0
    assert "Could not find" not in prompts.build_prompt(it)
