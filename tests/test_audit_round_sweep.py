"""브라우저 스윕은 라운드 종료 시 1회 — 단위 test 단계는 스윕 없이 done, 스윕 실패 시 반영 보류."""
import json

from scripts.audit import loop
from scripts.autopilot import notify, queue

def _p(tmp_path):
    p = tmp_path / "B.md"
    meta = {"stage": "queued", "mode": "auto", "attempts": 0, "deps": [], "kind": "code"}
    p.write_text(f"- **[U1]** 단위\n  <!-- autopilot: {json.dumps(meta)} -->\n", encoding="utf-8")
    return p


def _st():
    return {"phase": "test", "unit": "U1", "round": 1, "units_done": 0, "fails": 0, "fix": {}}


def test_unit_test_phase_runs_no_sweep(tmp_path, monkeypatch):
    monkeypatch.setattr(notify, "send", lambda *a, **k: True)
    p = _p(tmp_path)
    st = _st()
    loop.step(st, path=p, act={"sweep": lambda *a: (_ for _ in ()).throw(AssertionError("sweep")), "deploy": lambda n: {"ran": False}})
    assert queue.parse(p)[0].stage == "done" and st["units_done"] == 1 and st["phase"] == "develop"


def test_end_round_runs_full_sweep_and_holds_deploy_on_failure(monkeypatch):
    monkeypatch.setattr(notify, "send", lambda *a, **k: True)
    shipped = []
    st = {"round": 1, "units_done": 2, "phase": "develop", "unit": None, "fails": 0, "fix": {}}
    loop._end_round(st, lambda n: shipped.append(n) or {"ran": True, "outcome": "done"}, "x", None, full_sweep=lambda: (282, None))
    assert shipped == [2]
    st = {"round": 1, "units_done": 2, "phase": "develop", "unit": None, "fails": 0, "fix": {}}
    loop._end_round(st, lambda n: shipped.append(n) or {"ran": True, "outcome": "done"}, "x", None, full_sweep=lambda: (10, "overflow"))
    assert shipped == [2]
