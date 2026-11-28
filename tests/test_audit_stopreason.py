"""stopreason: 정지 사유 enum 과 자동 재개 정책."""
import pytest

from scripts.audit import stopreason as sr
from scripts.autopilot import queue


def test_stop_rejects_unknown_reason():
    with pytest.raises(ValueError):
        sr.stop({}, "bogus")


def test_is_stopped_follows_reason():
    st = {}
    assert not sr.is_stopped(st)
    sr.stop(st, sr.PACING)
    assert sr.is_stopped(st)


@pytest.mark.parametrize("reason", sr.AUTO_RESUME)
def test_resume_auto_reasons(reason):
    st = {"phase": "stopped"}
    sr.stop(st, reason)
    assert sr.resume(st) is True
    assert st["stop_reason"] is None and st["phase"] == "audit"


@pytest.mark.parametrize("reason", [sr.FAILED, sr.STOP_FLAG])
def test_resume_refused_for_failed_and_flag(reason):
    st = {"phase": "halted"}
    sr.stop(st, reason)
    assert sr.resume(st) is False
    assert st["stop_reason"] == reason and st["phase"] == "halted"


def test_resume_without_reason_is_noop_true():
    assert sr.resume({"phase": "develop"}) is True


def test_legacy_blocked_normalized(tmp_path):
    p = tmp_path / "BACKLOG.md"
    p.write_text('- **[U1]** x\n  <!-- autopilot: {"stage": "blocked", "mode": "auto", "attempts": 0, "deps": [], "kind": "code"} -->\n', encoding="utf-8")
    items = queue.parse(p)
    assert items and items[0].stage == "needs_decision"


def test_resume_at_recorded_once_and_restored_by_human():
    st = {"phase": "develop", "unit": "A-1", "round": 3, "fails": 2}
    sr.stop(st, sr.FAILED)
    sr.stop(st, sr.STOP_FLAG)  # 두 번째 stop 은 resume_at 을 덮지 않는다
    assert st["resume_at"] == {"phase": "develop", "unit": "A-1", "round": 3}
    assert sr.resume(st, human=True) is True
    assert st["phase"] == "develop" and st["unit"] == "A-1" and st["fails"] == 0 and "resume_at" not in st


def test_resume_timer_refuses_stop_flag_but_keeps_state():
    st = {"phase": "test", "unit": "A-2", "round": 1}
    sr.stop(st, sr.STOP_FLAG)
    assert sr.resume(st) is False and st["stop_reason"] == sr.STOP_FLAG


def test_pause_flag_is_human_resume_only():
    assert sr.PAUSE_FLAG in sr.HUMAN_RESUME and sr.PAUSE_FLAG not in sr.AUTO_RESUME


def test_resume_clears_stop_cause_and_describe():
    st = {"phase": "halted"}
    sr.stop(st, sr.FAILED)
    st["stop_cause"] = "원인X"
    assert "원인X" in sr.describe(st)
    sr.resume(st, human=True)
    assert "stop_cause" not in st


def test_blocked_is_human_resume_only():
    assert sr.BLOCKED in sr.HUMAN_RESUME and sr.BLOCKED not in sr.AUTO_RESUME
    st = {"phase": "develop"}
    sr.stop(st, sr.BLOCKED, cause="원인")
    assert st["stop_cause"] == "원인" and "원인" in sr.describe(st)
