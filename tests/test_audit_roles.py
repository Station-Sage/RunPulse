import json
from scripts.audit import roles, stopreason
from scripts.console import control


def test_set_flag_validates(tmp_path):
    p = tmp_path / "r.json"
    assert roles.set_flag("nobody", "paused", True, p)["ok"] is False
    assert roles.set_flag("designer", "bad", True, p)["ok"] is False
    assert roles.set_flag("designer", "paused", True, p)["roles"] == {"designer": {"paused": True}}
    assert roles.load(p)["designer"]["paused"] is True


def test_gate_none_without_flags(tmp_path):
    assert roles.gate({"phase": "audit"}, tmp_path / "r.json") is None


def test_gate_paused_stops_with_role_pause(tmp_path):
    p = tmp_path / "r.json"
    roles.set_flag("developer", "paused", True, p)
    st = {"phase": "develop"}
    assert "일시정지" in roles.gate(st, p)
    assert st["stop_reason"] == stopreason.ROLE_PAUSE and st["phase"] == "develop"


def test_gate_skip_persists_until_released(tmp_path):
    p = tmp_path / "r.json"
    roles.set_flag("designer", "skip", True, p)
    st = {"phase": "design"}
    assert "건너뜀" in roles.gate(st, p)
    assert st["phase"] == "develop" and roles.load(p)["designer"]["skip"] is True


def test_gate_rerun_consumes_flag(tmp_path):
    p = tmp_path / "r.json"
    roles.set_flag("verifier", "rerun", True, p)
    st = {"phase": "test"}
    assert "재실행" in roles.gate(st, p)
    assert st["phase"] == "test" and roles.load(p)["verifier"]["rerun"] is False


def test_resume_keeps_phase_on_role_pause(tmp_path):
    import json
    (tmp_path / "cycle_state.json").write_text(json.dumps({"phase": "develop", "stop_reason": "role_pause", "unit": "x"}))
    control._clear_stopped(tmp_path)
    st = json.loads((tmp_path / "cycle_state.json").read_text())
    assert st["phase"] == "develop" and st["stop_reason"] is None and st["unit"] == "x"


def test_resume_keeps_phase_on_pacing_stop(tmp_path):
    from scripts.console import control
    (tmp_path / "cycle_state.json").write_text(json.dumps(
        {"phase": "develop", "stop_reason": "pacing", "unit": "x", "cursor": {"phase": "develop", "round": 8}}))
    control._clear_stopped(tmp_path)
    st = json.loads((tmp_path / "cycle_state.json").read_text())
    assert st["phase"] == "develop" and st["stop_reason"] is None and st["cursor"]["round"] == 8


def test_resume_after_failed_still_restarts_audit(tmp_path):
    from scripts.console import control
    (tmp_path / "cycle_state.json").write_text(json.dumps({"phase": "halted", "stop_reason": "failed", "unit": "x"}))
    control._clear_stopped(tmp_path)
    assert json.loads((tmp_path / "cycle_state.json").read_text())["phase"] == "audit"


def test_blocked_for_helper_role(tmp_path):
    p = tmp_path / "r.json"
    assert roles.blocked("steward", p) is False
    roles.set_flag("steward", "paused", True, p)
    assert roles.blocked("steward", p) is True and roles.blocked("steward", p) is True  # 일시정지는 해제 전까지 유지
    roles.set_flag("steward", "paused", False, p)
    roles.set_flag("steward", "skip", True, p)
    assert roles.blocked("steward", p) is True and roles.blocked("steward", p) is True  # skip 은 해제 전까지 유지
