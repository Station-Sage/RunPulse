"""관제 제어 — 플래그·화이트리스트·타이머 drop-in·감사 로그."""
import json

from scripts.console import control


def test_pause_resume_stop(tmp_path):
    calls = []
    r = control.act("pause", tmp_path)
    assert r["pause"] and (tmp_path / "PAUSE").exists()
    r = control.act("stop", tmp_path, reap=lambda: [123])
    assert r["stop"] and r["killed"] == [123]
    r = control.act("start", tmp_path, run=lambda c: calls.append(c) or True)
    assert not r["pause"] and not r["stop"] and calls and "runpulse-audit.service" in calls[0]
    assert control.act("bogus", tmp_path)["ok"] is False
    assert len((tmp_path / "console_audit.jsonl").read_text().splitlines()) == 3


def test_tunables_validation(tmp_path):
    assert control.set_tunables({"AUDIT_TOOL_CALLS_PER_ROUND": 99}, tmp_path)["ok"] is False
    assert control.set_tunables({"NOPE": 1}, tmp_path)["ok"] is False
    assert control.set_tunables({"AUDIT_TOOL_CALLS_PER_ROUND": "x"}, tmp_path)["ok"] is False
    assert not (tmp_path / "tunables.json").exists()
    r = control.set_tunables({"AUDIT_TOOL_CALLS_PER_ROUND": "12", "FALLBACK_SESSION_MAX_USD": 20}, tmp_path)
    assert r["ok"] and json.loads((tmp_path / "tunables.json").read_text())["AUDIT_TOOL_CALLS_PER_ROUND"] == 12


def test_set_interval(tmp_path):
    ran = []
    ud = tmp_path / "units"
    r = control.set_interval("runpulse-audit", 45, tmp_path, ud, run=lambda c: ran.append(c) or True)
    assert r["ok"] and "OnUnitInactiveSec=45min" in (ud / "runpulse-audit.timer.d" / "interval.conf").read_text()
    assert ["systemctl", "--user", "daemon-reload"] in ran
    assert control.set_interval("runpulse-audit", 5, tmp_path, ud)["ok"] is False
    assert control.set_interval("evil", 30, tmp_path, ud)["ok"] is False
    assert control.set_interval("runpulse-audit", 30, tmp_path, ud, run=lambda c: False)["ok"] is False


def test_start_clears_stopped_cycle_state(tmp_path):
    import json
    p = tmp_path / "cycle_state.json"
    p.write_text(json.dumps({"phase": "stopped", "round": 7, "fails": 2, "unit": None, "stop_reason": "stop_flag"}))
    control.act("start", tmp_path, run=lambda c: True)
    st = json.loads(p.read_text())
    assert (st["phase"], st["stop_reason"], st["fails"], st["round"]) == ("audit", None, 0, 7)


def test_pause_keeps_cycle_state(tmp_path):
    import json
    p = tmp_path / "cycle_state.json"
    p.write_text(json.dumps({"phase": "stopped", "stop_reason": "stop_flag"}))
    control.act("pause", tmp_path)
    assert json.loads(p.read_text())["stop_reason"] == "stop_flag"


def test_resume_starts_loop_but_pause_does_not(tmp_path):
    calls = []
    run = lambda c: calls.append(c) or True
    control.act("pause", tmp_path, run=run)
    assert not calls
    control.act("resume", tmp_path, run=run)
    assert len(calls) == 1 and "runpulse-audit.service" in calls[0]


def test_resume_after_failed_halt_keeps_cursor(tmp_path):
    import json
    p = tmp_path / "cycle_state.json"
    p.write_text(json.dumps({"phase": "halted", "round": 8, "fails": 3, "unit": None, "stop_reason": "failed",
                             "cursor": {"phase": "develop", "unit": "X-1", "round": 8}}))
    control.act("resume", tmp_path, run=lambda c: True)
    st = json.loads(p.read_text())
    assert (st["phase"], st["unit"], st["fails"], st["stop_reason"], st["round"]) == ("develop", "X-1", 0, None, 8)
