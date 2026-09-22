"""scripts/autopilot/run_unit.py 테스트 — kind="code" 확장 부분만.

claude -p 서브프로세스 자체(_run_claude)는 실제 LLM 호출이라 여기서 테스트하지
않는다. 순수 함수(_build_prompt/_build_cmd)와, 독립 검증 게이트(_post_verify — 이번
확장의 핵심 안전장치)만 다룬다.
"""
from __future__ import annotations

from scripts.autopilot import queue, run_unit, settings


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
    def test_docs_kind_skips_verification(self, monkeypatch, tmp_path):
        monkeypatch.setattr(settings, "WORKTREE_DIR", tmp_path)
        ok, note = run_unit._post_verify(_docs_item())
        assert ok is True
        assert note == ""

    def test_code_kind_passes_when_command_succeeds(self, monkeypatch, tmp_path):
        monkeypatch.setattr(settings, "WORKTREE_DIR", tmp_path)
        ok, note = run_unit._post_verify(_code_item(verify=["true"]))
        assert ok is True
        assert note == ""

    def test_code_kind_fails_when_command_fails(self, monkeypatch, tmp_path):
        monkeypatch.setattr(settings, "WORKTREE_DIR", tmp_path)
        ok, note = run_unit._post_verify(_code_item(verify=["false"]))
        assert ok is False
        assert "false" in note

    def test_code_kind_defaults_to_full_pytest_when_verify_empty(self, monkeypatch, tmp_path):
        # exit 0로 치환한 가짜 pytest 커맨드로 "verify 비었을 때 기본값 사용"만 확인 —
        # 실제 tests/ 전체를 여기서 다시 돌리진 않는다(순환·비용 문제).
        monkeypatch.setattr(settings, "WORKTREE_DIR", tmp_path)
        item = _code_item(verify=[])
        assert item.verify == []
        # _post_verify가 기본 커맨드를 쓰는지는 문자열 자체를 확인하기보다,
        # WORKTREE_DIR에 pytest가 없어 실패하더라도 "기본값이 채워졌다"는 사실은
        # ok가 False + note에 pytest 관련 문구가 담기는 것으로 간접 확인한다.
        ok, note = run_unit._post_verify(item)
        assert ok is False
        assert "pytest" in note
