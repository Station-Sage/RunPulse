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
