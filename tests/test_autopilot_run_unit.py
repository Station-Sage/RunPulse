"""scripts/autopilot/run_unit.py 테스트 — kind="code" 확장 부분만.

claude -p 서브프로세스 자체(_run_claude)는 실제 LLM 호출이라 여기서 테스트하지
않는다. 순수 함수(_build_prompt/_build_cmd)와, 독립 검증 게이트(_post_verify — 이번
확장의 핵심 안전장치)만 다룬다.
"""
from __future__ import annotations

import pytest

from scripts.autopilot import leftovers, queue, run_unit, settings


def _code_item(**overrides) -> queue.QueueItem:
    base = dict(item_id="X", text="설명", kind="code", scope=["src/a.py"], verify=["true"])
    base.update(overrides)
    return queue.QueueItem(**base)


def _docs_item(**overrides) -> queue.QueueItem:
    base = dict(item_id="D", text="설명")
    base.update(overrides)
    return queue.QueueItem(**base)


class TestBuildPrompt:
    def test_docs_kind_uses_docs_template(self):
        prompt = run_unit._build_prompt(_docs_item())
        assert "설계 문서 작업" in prompt
        assert "[D]" in prompt

    def test_code_kind_uses_code_template_with_scope_and_verify(self):
        prompt = run_unit._build_prompt(_code_item())
        assert "코드 구현 작업" in prompt
        assert "src/a.py" in prompt
        assert "true" in prompt

    def test_code_kind_prompt_requires_following_embedded_spec(self):
        prompt = run_unit._build_prompt(_code_item())
        assert "구현 명세" in prompt
        assert "재사용" in prompt

    def test_code_kind_prompt_forbids_git_dash_c(self):
        prompt = run_unit._build_prompt(_code_item())
        assert "-C" in prompt and "옵션 없이" in prompt

    def test_code_kind_missing_scope_warns_instead_of_empty(self):
        item = _code_item(scope=[])
        prompt = run_unit._build_prompt(item)
        assert "scope 미지정" in prompt


class TestBuildCmd:
    def test_docs_kind_uses_base_allowed_tools_and_budget(self):
        cmd = run_unit._build_cmd("prompt", "docs")
        joined = " ".join(cmd)
        assert f"--max-budget-usd {settings.PER_RUN_MAX_USD}" in joined
        assert "Bash(npm install:*)" not in joined

    def test_code_kind_uses_code_allowed_tools_and_budget(self):
        cmd = run_unit._build_cmd("prompt", "code")
        joined = " ".join(cmd)
        assert f"--max-budget-usd {settings.PER_RUN_MAX_USD_CODE}" in joined
        assert "Bash(npm install:*)" in joined
        assert "Bash(python3 -m pytest:*)" in joined


class TestPostVerify:
    @pytest.fixture(autouse=True)
    def _worktree(self, monkeypatch, tmp_path):
        # 실제 autopilot 워크트리 유무와 무관하게 동작하도록 임시 디렉토리로 대체
        monkeypatch.setattr(run_unit.settings, "WORKTREE_DIR", tmp_path)

    def test_docs_kind_skips_verification(self, monkeypatch, tmp_path):
        ok, note = run_unit._post_verify(_docs_item())
        assert ok is True
        assert note == ""

    def test_code_kind_passes_when_command_succeeds(self, monkeypatch, tmp_path):
        ok, note = run_unit._post_verify(_code_item(verify=["true"]))
        assert ok is True
        assert note == ""

    def test_code_kind_fails_when_command_fails(self, monkeypatch, tmp_path):
        ok, note = run_unit._post_verify(_code_item(verify=["false"]))
        assert ok is False
        assert "false" in note

    def test_code_kind_defaults_to_full_pytest_when_verify_empty(self, monkeypatch, tmp_path):
        # exit 0로 치환한 가짜 pytest 커맨드로 "verify 비었을 때 기본값 사용"만 확인 —
        # 실제 tests/ 전체를 여기서 다시 돌리진 않는다(순환·비용 문제).
        item = _code_item(verify=[])
        assert item.verify == []
        # _post_verify가 기본 커맨드를 쓰는지는 문자열 자체를 확인하기보다,
        # WORKTREE_DIR에 pytest가 없어 실패하더라도 "기본값이 채워졌다"는 사실은
        # ok가 False + note에 pytest 관련 문구가 담기는 것으로 간접 확인한다.
        ok, note = run_unit._post_verify(item)
        assert ok is False
        assert "pytest" in note


class TestCommitLeftovers:
    """git이 막혀 모델이 커밋을 못 한 채 끝난 실행을 러너가 수습한다(scope 파일만)."""

    def _repo(self, tmp_path, monkeypatch):
        import subprocess

        def git(*a):
            return subprocess.run(["git", *a], cwd=tmp_path, capture_output=True, text=True, check=True)

        git("init", "-q")
        git("config", "user.email", "t@example.com")
        git("config", "user.name", "t")
        (tmp_path / "base.txt").write_text("x")
        git("add", "base.txt")
        git("commit", "-q", "-m", "base")
        return git

    def test_clean_worktree_is_noop(self, tmp_path, monkeypatch):
        self._repo(tmp_path, monkeypatch)
        assert leftovers.commit_leftovers(_code_item(scope=["src"]), tmp_path) == ""

    def test_commits_in_scope_files_only(self, tmp_path, monkeypatch):
        git = self._repo(tmp_path, monkeypatch)
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "a.py").write_text("print(1)")
        (tmp_path / "stray.db").write_text("junk")  # scope 밖 — 커밋되면 안 됨
        note = leftovers.commit_leftovers(_code_item(scope=["src/a.py"]), tmp_path)
        assert "1개를 러너가 커밋" in note
        assert "stray.db" in note
        tracked = git("ls-files").stdout.split()
        assert "src/a.py" in tracked
        assert "stray.db" not in tracked
        assert "chore(autopilot)" in git("log", "-1", "--format=%s").stdout

    def test_directory_scope_prefix_matches(self, tmp_path, monkeypatch):
        git = self._repo(tmp_path, monkeypatch)
        (tmp_path / "frontend" / "lib").mkdir(parents=True)
        (tmp_path / "frontend" / "lib" / "x.ts").write_text("export {}")
        leftovers.commit_leftovers(_code_item(scope=["frontend/lib"]), tmp_path)
        assert "frontend/lib/x.ts" in git("ls-files").stdout.split()


def test_abs_venv_rewrites_relative_venv_python():
    out = run_unit._abs_venv(".venv/bin/python -m pytest tests/ -q")
    assert out.startswith(str(run_unit.settings.PROJECT_ROOT)) and out.endswith("-m pytest tests/ -q")
    assert run_unit._abs_venv("true") == "true"
    out = run_unit._abs_venv("python3 -m pytest tests/ -q")
    assert out.endswith(".venv/bin/python -m pytest tests/ -q") and out.startswith("/")


class TestVerifyFailureRequeue:
    def _run(self, monkeypatch, tmp_path, attempts, note):
        recorded = {}
        cards = []
        monkeypatch.setattr(run_unit.gate, "check", lambda **k: type("G", (), {"allowed": True, "reason": ""})())
        monkeypatch.setattr(run_unit.queue, "parse", lambda p: [_code_item(attempts=attempts)])
        monkeypatch.setattr(run_unit.queue, "next_runnable", lambda items: items[0])
        monkeypatch.setattr(run_unit.worktree, "ensure", lambda: None)
        monkeypatch.setattr(run_unit.worktree, "sync", lambda: None)
        monkeypatch.setattr(run_unit.worktree, "_run", lambda *a, **k: type("R", (), {"stdout": ""})())
        monkeypatch.setattr(run_unit, "_run_claude", lambda it: {"outcome": "success", "duration_s": 1})
        monkeypatch.setattr(run_unit, "_decisions_changed", lambda: False)
        monkeypatch.setattr(run_unit, "_post_verify", lambda it: (False, note))
        monkeypatch.setattr(run_unit, "_register_failed_card", lambda it, k, r: cards.append(k))
        monkeypatch.setattr(run_unit.decisions, "append", lambda recs, *a, **k: cards.extend(r["kind"] for r in recs))
        monkeypatch.setattr(run_unit.ledger, "append", lambda e: None)
        monkeypatch.setattr(run_unit.notify, "send", lambda m: None)
        monkeypatch.setattr(run_unit.queue, "update_item",
                            lambda path, iid, **kw: recorded.update(kw))
        monkeypatch.setattr(run_unit.settings, "STATE_DIR", tmp_path)
        monkeypatch.setattr(run_unit.settings, "LOCK_PATH", tmp_path / "lock")
        run_unit.run_once()
        return recorded, cards

    def test_first_verify_failure_requeues_without_card(self, monkeypatch, tmp_path):
        rec, cards = self._run(monkeypatch, tmp_path, 0, "`x` 종료코드 1\nFAILED")
        assert rec["stage"] == "queued" and rec["fail_kind"] == "verify" and cards == []

    def test_env_failure_provisions_then_requeues_without_card(self, monkeypatch, tmp_path):
        monkeypatch.setattr(run_unit.worktree, "provision", lambda: [".venv"])
        rec, cards = self._run(monkeypatch, tmp_path, 0, "Cannot find module 'playwright'")
        assert rec["stage"] == "queued" and rec["fail_kind"] == "env" and cards == []
        assert ".venv" in rec["fail_reason"]

    def test_env_failure_unfixable_fails_with_card(self, monkeypatch, tmp_path):
        monkeypatch.setattr(run_unit.worktree, "provision", lambda: [])
        rec, cards = self._run(monkeypatch, tmp_path, 0, "Cannot find module './local.js'")
        assert rec["stage"] == "needs_decision" and cards == ["verify_decision"]

    def test_second_verify_failure_still_retries(self, monkeypatch, tmp_path):
        rec, cards = self._run(monkeypatch, tmp_path, 1, "`x` 종료코드 1\nFAILED")
        assert rec["stage"] == "queued" and cards == []

    def test_third_verify_failure_fails_with_card(self, monkeypatch, tmp_path):
        rec, cards = self._run(monkeypatch, tmp_path, 2, "`x` 종료코드 1\nFAILED")
        assert rec["stage"] == "needs_decision" and cards == ["verify_decision"]


def test_sync_block_holds_item_in_queue(monkeypatch, tmp_path):
    updates = []
    monkeypatch.setattr(run_unit.gate, "check", lambda **k: type("G", (), {"allowed": True, "reason": ""})())
    monkeypatch.setattr(run_unit.queue, "parse", lambda p: [_code_item(attempts=0)])
    monkeypatch.setattr(run_unit.queue, "next_runnable", lambda items: items[0])
    monkeypatch.setattr(run_unit.worktree, "ensure", lambda: None)
    monkeypatch.setattr(run_unit.worktree, "sync", lambda: "worktree 차단")
    monkeypatch.setattr(run_unit.notify, "send", lambda m: None)
    monkeypatch.setattr(run_unit.queue, "update_item", lambda path, iid, **kw: updates.append(kw))
    monkeypatch.setattr(run_unit.settings, "STATE_DIR", tmp_path)
    monkeypatch.setattr(run_unit.settings, "LOCK_PATH", tmp_path / "lock")
    assert run_unit.run_once() == 3
    assert not any(u.get("stage") == "failed" for u in updates)


def test_verify_card_options_and_fresh_append(tmp_path):
    from scripts.audit import decisions
    from scripts.autopilot import verify_card
    c = verify_card.build_verify_card("A-1", "real", "실패", "작업")
    assert c["kind"] == "verify_decision" and [o["action"] for o in c["options"]][-1] == "dropped"
    p = tmp_path / "d.json"
    decisions.append([c], p)
    decisions.append([verify_card.build_verify_card("A-1", "real", "다시", "작업")], p, fresh=True)
    assert len(decisions.load(p)) == 1
