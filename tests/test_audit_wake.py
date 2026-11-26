"""pacing 재개 시각 일회성 타이머 예약 테스트."""
from scripts.audit import wake


def test_schedule_builds_transient_timer():
    calls = []
    ok = wake.schedule(1000 + 600, now=1000, run=lambda a: calls.append(a) or 0)
    assert ok
    assert calls[0][-1] == f"{wake.UNIT}.timer"
    assert f"--on-active={600 + wake.MARGIN_SEC}s" in calls[1]
    assert calls[1][-1] == wake.SERVICE


def test_schedule_skips_without_resume_at():
    calls = []
    assert wake.schedule(None, run=lambda a: calls.append(a) or 0) is False
    assert calls == []


def test_schedule_past_time_uses_margin():
    calls = []
    wake.schedule(500, now=1000, run=lambda a: calls.append(a) or 0)
    assert f"--on-active={wake.MARGIN_SEC}s" in calls[1]


def test_sync_cancels_when_allowed_and_reschedules_when_blocked():
    from scripts.audit import wake
    from scripts.autopilot.pacing import Pacing
    calls = []
    run = lambda a: calls.append(a) or 0
    assert wake.sync(1000.0, run, lambda n: Pacing(True)) is False
    assert calls == [["systemctl", "--user", "stop", "runpulse-pacing-wake.timer"]]
    calls.clear()
    assert wake.sync(1000.0, run, lambda n: Pacing(False, "x", 4600.0)) is True
    assert any("--on-active=3660s" in a for c in calls for a in c)
