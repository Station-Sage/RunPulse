"""decision_guard — DECISIONS.md 결정 상태 vs BACKLOG.md stage 불일치 검출."""
from scripts.audit import decision_guard


def _backlog(tmp_path, stage, item_id="AUD-x"):
    p = tmp_path / "BACKLOG.md"
    p.write_text(f'- **[{item_id}]** 설명\n  <!-- autopilot: {{"stage":"{stage}","mode":"auto","attempts":0,"deps":[]}} -->\n')
    return p


def _decisions(tmp_path, body):
    p = tmp_path / "DECISIONS.md"
    p.write_text(body)
    return p


def test_latest_statuses_picks_last_occurrence():
    md = (
        "## [AUD-x] 제목\n- **상태**: 사용자 결정 대기.\n\n"
        "## [AUD-x] 재확인\n- **상태**: 확정, 구현 완료.\n"
    )
    assert decision_guard.latest_statuses(md) == {"AUD-x": "확정, 구현 완료."}


def test_pending_status_but_stage_not_needs_decision_is_flagged(tmp_path):
    bl = _backlog(tmp_path, "done")
    dec = _decisions(tmp_path, "## [AUD-x] 제목\n- **상태**: 사용자 결정 대기. 코드 변경 없음.\n")
    problems = decision_guard.find_mismatches(bl, dec)
    assert len(problems) == 1 and "AUD-x" in problems[0]


def test_pending_status_with_needs_decision_stage_is_clean(tmp_path):
    bl = _backlog(tmp_path, "needs_decision")
    dec = _decisions(tmp_path, "## [AUD-x] 제목\n- **상태**: 사용자 결정 대기.\n")
    assert decision_guard.find_mismatches(bl, dec) == []


def test_no_code_done_without_pending_wording_is_flagged(tmp_path):
    bl = _backlog(tmp_path, "done")
    dec = _decisions(tmp_path, "## [AUD-x] 제목\n- **상태**: scope 파일 전부 미수정.\n")
    problems = decision_guard.find_mismatches(bl, dec)
    assert len(problems) == 1


def test_resolved_decision_with_done_stage_is_clean(tmp_path):
    bl = _backlog(tmp_path, "done")
    dec = _decisions(tmp_path, "## [AUD-x] 제목\n- **상태**: 사용자 확정(A안). 구현 완료.\n")
    assert decision_guard.find_mismatches(bl, dec) == []


def test_missing_decisions_file_is_clean(tmp_path):
    bl = _backlog(tmp_path, "queued")
    assert decision_guard.find_mismatches(bl, tmp_path / "DECISIONS.md") == []
