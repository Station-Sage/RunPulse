"""verify 진단·lint·재시도 분기."""
from pathlib import Path

from scripts.autopilot import prompts, queue, run_unit, verify_doctor as vd


def test_diagnose():
    assert vd.diagnose("x", 127, "") == "env"
    assert vd.diagnose("npx vitest run a.test.ts", 1, "No test files found") == "missing_target"
    assert vd.diagnose("node s.mjs", 1, "ERR_INVALID_ARG_TYPE") == "usage"
    assert vd.diagnose("! grep -rn foo src", 1, "src/a:9: foo") == "absence_hit"
    assert vd.diagnose("pytest", 1, "assert 1 == 2") == "real"


def test_reason_tag_and_stop():
    r = vd.tag_reason("usage", "boom")
    assert vd.split_reason(r) == ("usage", "boom")
    assert vd.should_stop(1, "usage", r) and not vd.should_stop(1, "real", r)
    assert vd.should_stop(3, "real", "") and not vd.should_stop(2, "absence_hit", "")


def test_retry_hint_contains_output():
    assert "전체출력" in vd.retry_hint("absence_hit", "전체출력")
    assert "테스트 파일" in vd.retry_hint("missing_target", "x")


def test_lint(tmp_path: Path):
    (tmp_path / "ok.test.mjs").write_text("")
    assert vd.lint(["node --test ok.test.mjs"], [], tmp_path) == []
    assert vd.lint(["node --test no.test.mjs"], [], tmp_path)
    assert vd.lint(["node --test no.test.mjs"], ["no.test.mjs"], tmp_path) == []
    assert vd.lint(["node scripts/x.mjs"], [], tmp_path)
    assert vd.missing_file("cd frontend && npx vitest run src/a.test.ts", "") == "frontend/src/a.test.ts"


def _item(tmp_path, attempts=0, reason=""):
    q = tmp_path / "q.md"
    q.write_text('- **[F-1]** 작업\n  <!-- autopilot: {"stage":"in_progress","mode":"auto","attempts":%d,"deps":[],"kind":"code","scope":["src/a.py"]} -->\n' % attempts, encoding="utf-8")
    it = queue.parse(q)[0]
    it.fail_reason = reason
    return it


def test_handle_missing_target_extends_scope_then_stops(tmp_path, monkeypatch):
    cards = []
    monkeypatch.setattr(run_unit.decisions, "append", lambda recs, *a, **k: cards.extend(recs))
    note = "`node --test tests/x.test.mjs` 종료코드 1\nCould not find"
    stage, extra = run_unit._handle_verify_failure(_item(tmp_path), note)
    assert stage == "queued" and "tests/x.test.mjs" in extra["scope"] and not cards
    stage, _ = run_unit._handle_verify_failure(_item(tmp_path, 1, extra["fail_reason"]), note)
    assert stage == "needs_decision" and cards  # 같은 원인 반복 → 결정 카드


def test_prompt_uses_hint(tmp_path):
    it = _item(tmp_path, 1, vd.tag_reason("absence_hit", "src/a:9"))
    it.fail_kind = "verify"
    assert "src/a:9" in prompts.build_prompt(it)


def test_lint_absence_baseline_outside_scope(tmp_path):
    from scripts.autopilot import verify_doctor as vd
    (tmp_path / "src").mkdir()
    (tmp_path / "src/a.txt").write_text("bad\n")
    cmd = "! grep -rn bad src"
    assert any("범위 밖" in p for p in vd.lint([cmd], ["src/b.txt"], tmp_path))
    assert vd.lint([cmd], ["src/a.txt"], tmp_path) == []  # 범위 안 적중은 항목이 고칠 대상
    assert vd.lint(["! grep -rn zzz src"], [], tmp_path) == []  # 적중 없음


def test_tag_reason_puts_errors_before_warnings():
    out = "Warn: unused css\nhint: x\nfoo\nError: Cannot find module 'vitest'\nbar"
    r = vd.tag_reason("real", out)
    assert "Warn" not in r and "hint" not in r
    assert r.index("Cannot find module") < r.index("bar")


def test_missing_package():
    assert vd.missing_package("Error: Cannot find module 'vitest'") == ("npm", "vitest")
    assert vd.missing_package("Cannot find package '@sveltejs/kit' imported") == ("npm", "@sveltejs/kit")
    assert vd.missing_package("ModuleNotFoundError: No module named 'yaml'") == ("pip", "yaml")
    assert vd.missing_package("No module named pytest") == ("", "")
    assert vd.missing_package("Cannot find module './local.js'") == ("", "")


def test_lint_rejects_uninstalled_runner(tmp_path: Path):
    (tmp_path / "frontend").mkdir()
    (tmp_path / "frontend/a.test.ts").write_text("")
    probs = vd.lint(["cd frontend && npx vitest run a.test.ts"], [], tmp_path)
    assert any("vitest" in p for p in probs)
    (tmp_path / "frontend/package.json").write_text('{"devDependencies": {"vitest": "1"}}')
    assert not any("러너" in p for p in vd.lint(["cd frontend && npx vitest run a.test.ts"], [], tmp_path))


def test_handle_missing_dep_registers_install_card(tmp_path, monkeypatch):
    from scripts.audit import decisions
    from scripts.autopilot import worktree
    got = []
    monkeypatch.setattr(worktree, "provision", lambda: [])
    monkeypatch.setattr(decisions, "append", lambda recs, *a: got.extend(recs))
    note = "`npm run check` 종료코드 1\nError: Cannot find module 'vitest'"
    stage, extra = run_unit._handle_verify_failure(_item(tmp_path), note)
    assert stage == "needs_decision" and extra["fail_kind"] == "env"
    assert got[0]["dep"] == {"eco": "npm", "name": "vitest"}


COUNT_CMD = "cd frontend && test $(grep -rn 'heroView' src | wc -l) -eq 0"


def test_count_absence_is_absence_hit():
    assert vd.is_absence_check(COUNT_CMD) and not vd.is_absence_check("pytest")
    assert vd.diagnose(COUNT_CMD, 1, "") == "absence_hit"


def test_hit_target_finds_out_of_scope_file(tmp_path):
    (tmp_path / "frontend/src/a").mkdir(parents=True)
    (tmp_path / "frontend/src/a/p.ts").write_text("heroView\n")
    assert vd.hit_target(COUNT_CMD, [], tmp_path) == "frontend/src/a/p.ts"
    assert vd.hit_target(COUNT_CMD, ["frontend/src/a"], tmp_path) == ""
    assert vd.hit_target("pytest", [], tmp_path) == ""


def test_handle_absence_hit_extends_scope(tmp_path, monkeypatch):
    (tmp_path / "frontend/src").mkdir(parents=True)
    (tmp_path / "frontend/src/p.ts").write_text("heroView\n")
    monkeypatch.setattr(run_unit.settings, "WORKTREE_DIR", tmp_path)
    note = f"`{COUNT_CMD}` 종료코드 1\n"
    stage, extra = run_unit._handle_verify_failure(_item(tmp_path), note)
    assert stage == "queued" and "frontend/src/p.ts" in extra["scope"]
