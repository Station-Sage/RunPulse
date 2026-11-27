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


def test_end_round_sweep_failure_runs_fix_round_then_gives_up(monkeypatch, tmp_path):
    monkeypatch.setattr(notify, "send", lambda *a, **k: True)
    q = tmp_path / "B.md"
    q.write_text("", encoding="utf-8")
    shipped = []
    ship = lambda n: shipped.append(n) or {"ran": True, "outcome": "done"}
    st = {**loop._INIT, "round": 1, "units_done": 2, "phase": "develop"}
    loop._end_round(st, ship, "x", q, full_sweep=lambda: (282, None))
    assert shipped == [2] and st["round"] == 2 and st["sweep_fix"] == 0
    st = {**loop._INIT, "round": 1, "units_done": 2, "phase": "audit"}
    for k in (1, 2):  # 실패 → 수정 단위 추가, 개발 재진입, 라운드·반영 그대로
        loop._end_round(st, ship, "x", q, full_sweep=lambda: (10, "overflow"))
        assert (st["phase"], st["round"], st["units_done"], st["sweep_fix"]) == ("develop", 1, 2, k) and shipped == [2]
    from scripts.autopilot import queue
    its = queue.parse(q)
    assert [i.item_id for i in its] == ["SWEEP-R1-1", "SWEEP-R1-2"] and its[0].stage == "queued" and "overflow" in its[0].scope[1]
    loop._end_round(st, ship, "x", q, full_sweep=lambda: (10, "overflow"))  # 상한 초과 → 반영 보류, 다음 라운드
    assert shipped == [2] and st["round"] == 2 and st["sweep_fix"] == 0
