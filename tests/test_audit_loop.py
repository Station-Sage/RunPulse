"""P6 — 중첩 반복 오케스트레이터(상태 복원·승인 게이트·스윕 안쪽 루프·정지 조건)."""
import json

import pytest

from scripts.audit import loop
from scripts.autopilot import queue

F = [{"perspective": "ux", "kind": "tap", "verdict": "real", "impact": "작음", "fix": "키움"}]


@pytest.fixture(autouse=True)
def _no_release(monkeypatch):
    monkeypatch.setattr(loop.release, "due", lambda *a, **k: False)
    monkeypatch.setattr(loop.deploy, "run", lambda n: {"ran": False, "reason": "테스트"})


def _backlog(tmp_path, stage="queued"):
    p = tmp_path / "B.md"
    meta = {"stage": stage, "mode": "auto", "attempts": 0, "deps": [], "kind": "code"}
    p.write_text(f"- **[U1]** 단위\n  <!-- autopilot: {json.dumps(meta)} -->\n", encoding="utf-8")
    return p


def _st(phase, **kw):
    return {**loop._INIT, "phase": phase, **kw}


def _quiet(monkeypatch):
    monkeypatch.setattr(loop.notify, "send", lambda t: True)
    monkeypatch.setattr(loop.pacing, "check", lambda n: type("P", (), {"allowed": True, "reason": ""})())


def test_state_roundtrip_and_default(tmp_path):
    p = tmp_path / "s.json"
    assert loop.load_state(p)["phase"] == "audit"
    loop.save_state(_st("test", unit="U1"), p)
    assert loop.load_state(p)["unit"] == "U1"


def test_propose_blocked_and_idempotent(tmp_path, monkeypatch):
    monkeypatch.setattr(loop, "PENDING_PATH", tmp_path / "pending.md")
    p = _backlog(tmp_path)
    assert len(loop.propose(F, p)) == 1
    assert loop.propose(F, p) == []
    new = [i for i in queue.parse(p) if i.item_id.startswith("AUD-")][0]
    assert new.stage == "blocked" and new.mode == "auto"
    assert queue.next_runnable([new]) is None


def test_user_blocked_items_do_not_stall_loop(tmp_path, monkeypatch):
    _quiet(monkeypatch)
    p = _backlog(tmp_path, "blocked")
    called = []
    st = _st("develop")
    msg = loop.step(st, path=p, act={"develop": lambda: called.append(1) or 0})
    assert not called and st["phase"] == "audit" and "다음 감사" in msg


def test_legacy_await_state_resumes_like_develop(tmp_path, monkeypatch):
    _quiet(monkeypatch)
    p = _backlog(tmp_path, "queued")
    called = []
    loop.step(_st("await"), path=p, act={"develop": lambda: called.append(1) or 0})
    assert called


def test_develop_then_test_sweep_inside_inner_loop(tmp_path, monkeypatch):
    _quiet(monkeypatch)
    p = _backlog(tmp_path)
    st = _st("develop")
    loop.step(st, path=p, act={"develop": lambda: queue.update_item(p, "U1", stage="review") or 0})
    assert st["phase"] == "test" and st["unit"] == "U1"
    loop.step(st, path=p, act={"sweep": lambda: (282, None)})
    assert queue.parse(p)[0].stage == "done" and st["phase"] == "develop" and st["units_done"] == 1


def test_sweep_failure_requeues_then_blocks(tmp_path, monkeypatch):
    _quiet(monkeypatch)
    p = _backlog(tmp_path, "review")
    st = _st("test", unit="U1")
    for _ in range(loop.FIX_LIMIT):
        loop.step(st, path=p, act={"sweep": lambda: (10, "overflow")})
        assert queue.parse(p)[0].stage == "queued"
        queue.update_item(p, "U1", stage="review")
        st["phase"] = "test"
    loop.step(st, path=p, act={"sweep": lambda: (10, "overflow")})
    assert queue.parse(p)[0].stage == "blocked"


def test_round_ends_and_unit_cap(tmp_path, monkeypatch):
    _quiet(monkeypatch)
    st = _st("develop")
    assert "다음 감사" in loop.step(st, path=_backlog(tmp_path, "done"))
    assert st["phase"] == "audit" and st["round"] == 2
    st = _st("develop", units_done=loop.UNIT_CAP)
    assert "상한" in loop.step(st, path=_backlog(tmp_path))


def test_audit_failures_halt_and_pacing_block(tmp_path, monkeypatch):
    _quiet(monkeypatch)
    st = _st("audit")
    bad = {"audit": lambda: {"ran": True, "outcome": "sweep_failed", "reason": "x"}}
    for _ in range(loop.FAIL_LIMIT):
        loop.step(st, path=_backlog(tmp_path), act=bad)
    assert st["phase"] == "halted"
    monkeypatch.setattr(loop.pacing, "check", lambda n: type("P", (), {"allowed": False, "reason": "한도"})())
    assert "pacing" in loop.step(_st("audit"), path=_backlog(tmp_path))


def test_audit_phase_runs_release_audit_when_version_due(tmp_path, monkeypatch):
    _quiet(monkeypatch)
    monkeypatch.setattr(loop.release, "due", lambda *a, **k: True)
    monkeypatch.setattr(loop.release, "version", lambda *a, **k: "9.9.9")
    st = _st("audit")
    act = {"release": lambda: {"ran": True, "outcome": "done", "confirmed": 2},
           "audit": lambda: (_ for _ in ()).throw(AssertionError("일반 감사 호출 금지"))}
    assert "감사 완료" in loop.step(st, path=_backlog(tmp_path), act=act)
    assert st["phase"] == "design"


def test_audit_phase_falls_back_to_normal_when_release_blocked(tmp_path, monkeypatch):
    _quiet(monkeypatch)
    monkeypatch.setattr(loop.release, "due", lambda *a, **k: True)
    act = {"release": lambda: {"ran": False, "reason": "Opus 한도"},
           "audit": lambda: {"ran": True, "outcome": "done", "confirmed": 0}}
    st = _st("audit")
    assert "감사 완료" in loop.step(st, path=_backlog(tmp_path), act=act)


def test_round_end_deploys_when_units_done_and_reports_failure(tmp_path, monkeypatch):
    sent = []
    monkeypatch.setattr(loop.notify, "send", lambda t: sent.append(t) or True)
    monkeypatch.setattr(loop.pacing, "check", lambda n: type("P", (), {"allowed": True, "reason": ""})())
    calls = []
    ok = lambda n: calls.append(n) or {"ran": True, "outcome": "done", "commits": 2, "reason": "빌드 성공"}
    st = _st("develop", units_done=2)
    msg = loop.step(st, path=_backlog(tmp_path, "done"), act={"deploy": ok})
    assert calls == [2] and "운영 반영 완료" in msg and st["units_done"] == 0 and st["phase"] == "audit"
    bad = lambda n: {"ran": True, "outcome": "failed", "reason": "갈라짐"}
    st = _st("develop", units_done=1)
    msg = loop.step(st, path=_backlog(tmp_path, "done"), act={"deploy": bad})
    assert "운영 반영 실패" in msg and st["phase"] == "audit" and "사람 확인" in sent[-1]


def test_run_until_stop_chains_steps_and_stops_on_skip(tmp_path, monkeypatch):
    monkeypatch.setattr(loop.notify, "send", lambda t: True)
    monkeypatch.setattr(loop, "agents_confirmed", lambda: [])
    monkeypatch.setattr(loop.pacing, "check", lambda n: type("P", (), {"allowed": True, "reason": ""})())
    act = {"audit": lambda: {"ran": False, "reason": "간격"}}
    out = loop.run_until_stop(_st("design"), path=_backlog(tmp_path, "done"), act=act)
    assert len(out) == 2 and out[0].startswith("새 후보 없음") and out[1].startswith("감사 생략")
    assert len(loop.run_until_stop(_st("design"), path=_backlog(tmp_path, "done"), act=act, once=True)) == 1
