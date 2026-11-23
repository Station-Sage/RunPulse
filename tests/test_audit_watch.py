"""audit/watch.py — 문제 판정과 중복 알림 억제."""
from scripts.audit import watch

OK = {"timer": "active", "running": True, "phase": "develop", "log_age_min": 3.0, "last_cycle": "done"}


def test_problems_detects_each_failure():
    assert watch.problems(OK) == []
    assert "타이머" in watch.problems({**OK, "timer": "inactive"})[0]
    assert "halted" in watch.problems({**OK, "phase": "halted"})[0]
    assert "정체" in watch.problems({**OK, "log_age_min": 90})[0]
    assert watch.problems({**OK, "running": False, "log_age_min": 90}) == []
    assert "사이클" in watch.problems({**OK, "last_cycle": "sweep_failed"})[0]


def test_check_alerts_on_change_only_and_reports_recovery(tmp_path):
    sent, p = [], tmp_path / "w.json"
    send = lambda t: sent.append(t) or True
    bad = {**OK, "phase": "halted"}
    watch.check(bad, p, send)
    watch.check(bad, p, send)
    assert len(sent) == 1
    watch.check(OK, p, send)
    assert len(sent) == 2 and "복구" in sent[1]
    watch.check(OK, p, send)
    assert len(sent) == 2
