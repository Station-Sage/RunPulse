"""failed 처리 — 분류·asked 카드·선택 반영(consume)·프롬프트 주입·콘솔 요약."""
from scripts.audit import consume, decisions
from scripts.autopilot import fail_handling as fh, prompts, queue
from scripts.console import overview

SEC = """## [AUD-1] 제목 후보
- **배경**: 이미 구현됨
- **질문**: 어떻게 할까
- **선택지**:
  1. 옵션하나
  2. 옵션둘
- **권고**: 2번
"""


def _q(tmp_path, stage, meta=""):
    q = tmp_path / "B.md"
    q.write_text(f'- **[AUD-1]** 제목\n  <!-- autopilot: {{"stage":"{stage}","mode":"auto","attempts":0,"deps":[]{meta}}} -->\n')
    return q


def _card(tmp_path, card):
    dp = tmp_path / "d.json"
    decisions.append([card], dp)
    return dp


def test_classify_verify():
    assert fh.classify_verify(127, "") == "env"
    assert fh.classify_verify(1, "No module named pytest") == "env"
    assert fh.classify_verify(1, "Error: Cannot find module './x.mjs'") == "env"
    assert fh.classify_verify(1, "FAILED x") == "verify"


def test_parse_and_asked_card():
    sec = fh.pick_section(fh.parse_sections(SEC), "AUD-1")
    assert sec["options"] == ["옵션하나", "옵션둘"]
    c = fh.build_asked_card("AUD-1", sec, "제목", 1)
    assert [o["action"] for o in c["options"]] == ["scope", "scope", "already_done", "dropped", "redefine"]
    assert c["recommendation"] == "B" and c["rounds"] == 1


def test_scope_choice_appends_scope_and_answered(tmp_path):
    q = _q(tmp_path, "needs_decision")
    dp = _card(tmp_path, fh.build_asked_card("AUD-1", fh.parse_sections(SEC)[0], "제목", 1))
    decisions.choose("AUD-1", "A", dp, text="세부")
    consume.apply(q, lambda f: {}, dp)
    it = queue.parse(q)[0]
    assert it.stage == "queued" and it.answered == ["AUD-1"] and "옵션하나" in it.scope[-1] and "세부" in it.scope[-1]
    assert "답변 완료" in prompts.build_prompt(it)


def test_done_and_dropped(tmp_path):
    for key, res in (("C", "already_done"), ("D", "dropped")):
        q = _q(tmp_path, "needs_decision")
        dp = _card(tmp_path, fh.build_asked_card("AUD-1", fh.parse_sections(SEC)[0], "제목", 1))
        decisions.choose("AUD-1", key, dp)
        consume.apply(q, lambda f: {}, dp)
        it = queue.parse(q)[0]
        assert it.stage == "done" and it.resolution == res
        (tmp_path / "d.json").unlink()


def test_failed_env_retry_resets_verify(tmp_path):
    q = _q(tmp_path, "failed", ',"fail_kind":"env","fail_reason":"x","fails":1')
    dp = _card(tmp_path, fh.build_failed_card("AUD-1", "env", "rc127", "제목"))
    decisions.choose("AUD-1", "A", dp)
    consume.apply(q, lambda f: {}, dp)
    it = queue.parse(q)[0]
    assert it.stage == "queued" and it.verify == [fh.DEFAULT_VERIFY] and it.fail_kind == ""


def test_redefine_text_becomes_scope(tmp_path):
    q = _q(tmp_path, "failed", ',"fail_kind":"asked_loop"')
    dp = _card(tmp_path, fh.build_failed_card("AUD-1", "asked_loop", "loop", "제목"))
    decisions.choose("AUD-1", "A", dp, text="새 지시")
    consume.apply(q, lambda f: {}, dp)
    it = queue.parse(q)[0]
    assert it.stage == "queued" and it.scope == ["새 지시"]


def test_sync_has_only_drop_option():
    assert [o["action"] for o in fh.build_failed_card("X", "sync", "dirty", "t")["options"]] == ["dropped"]


def test_console_blocked_split(tmp_path):
    q = _q(tmp_path, "failed", ',"fail_kind":"verify","fail_reason":"pytest 실패"')
    s = overview.queue_summary(q)
    assert s["attention"] == [] and s["blocked"][0]["kind"] == "verify" and s["blocked_count"] == 1


def test_migrate_failed(tmp_path):
    from scripts.autopilot import migrate_failed
    q = _q(tmp_path, "failed")
    md = tmp_path / "DECISIONS.md"
    md.write_text(SEC, encoding="utf-8")
    dp = tmp_path / "d.json"
    assert migrate_failed.migrate(q, md, dp) == ["AUD-1"] and queue.parse(q)[0].stage == "failed"
    assert migrate_failed.migrate(q, md, dp, apply=True) == ["AUD-1"]
    it = queue.parse(q)[0]
    assert it.stage == "needs_decision" and it.fail_kind == "asked" and it.asks == 1
    assert decisions.load(dp)[0]["id"] == "AUD-1"
