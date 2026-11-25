from types import SimpleNamespace as NS

from scripts.audit import loop, orchestrator as o, stopreason


def _it(stage):
    return NS(stage=stage)


def test_record_round_resets_on_new_defects():
    st = {}
    o.record_round(st, 0)
    assert st["gate"] == {"clean_rounds": 1, "version_rounds": 1}
    o.record_round(st, 2)
    assert st["gate"] == {"clean_rounds": 0, "version_rounds": 2}


def test_gate_requires_clean_rounds_and_empty_queue():
    st = {}
    o.record_round(st, 0)
    assert o.gate_passed(st, [])[0] is False
    o.record_round(st, 0)
    assert o.gate_passed(st, [_it("done")])[0] is True
    assert o.gate_passed(st, [_it("queued")])[0] is False
    assert o.gate_passed(st, [_it("failed")])[0] is False


def test_gate_round_cap():
    st = {"gate": {"clean_rounds": 0, "version_rounds": o.MAX_ROUNDS}}
    ok, why = o.gate_passed(st, [_it("queued")])
    assert ok and "상한" in why


def test_after_round_sets_plan_phase():
    st = {"phase": "audit", "round_new": 0, "gate": {"clean_rounds": 1, "version_rounds": 1}}
    assert o.after_round(st, []) is not None and st["phase"] == "plan" and "round_new" not in st


def test_plan_step_without_planner_awaits_user():
    st = {}
    o.plan_step(st)
    assert st["stop_reason"] == stopreason.AWAIT_DECISION
    assert stopreason.resume(st) is False
    assert o.plan_step({}, lambda s: "계획") == "계획"


def test_end_round_routes_to_plan_when_gate_passes(tmp_path):
    q = tmp_path / "BACKLOG.md"
    q.write_text("", encoding="utf-8")
    st = {**loop._INIT, "gate": {"clean_rounds": 1, "version_rounds": 1}, "fix": {}}
    loop._end_round(st, lambda n: {"ran": False}, "x", q)
    assert st["phase"] == "plan" and st["gate"]["clean_rounds"] == 2
    msg = loop.step(st, path=q, act={"plan": lambda s: "기획 완료"}, force=True)
    assert msg == "기획 완료"


def _crit_queue(tmp_path, stage="queued"):
    from scripts.autopilot import queue
    q = tmp_path / "BACKLOG.md"
    q.write_text('- **[A-1]** a\n  <!-- autopilot: {"stage":"queued","mode":"auto","attempts":0,"deps":[]} -->\n'
                 '- **[C-1]** c\n  <!-- autopilot: {"stage":"%s","mode":"auto","attempts":0,"deps":[],"critical":true} -->\n' % stage, encoding="utf-8")
    return q, queue


def test_critical_parsed_and_preferred(tmp_path):
    q, queue = _crit_queue(tmp_path)
    items = queue.parse(q)
    assert [i.critical for i in items] == [False, True]
    assert queue.next_runnable(items).item_id == "C-1"
    queue.update_item(q, "C-1", stage="review")
    assert queue.parse(q)[1].critical is True and queue.next_runnable(queue.parse(q)).item_id == "A-1"


def test_critical_blocks_gate_and_plan(tmp_path):
    q, queue = _crit_queue(tmp_path)
    assert o.critical_open(queue.parse(q)) == ["C-1"]
    st = {"gate": {"clean_rounds": 5, "version_rounds": 1}}
    ok, why = o.gate_passed(st, [i for i in queue.parse(q) if i.critical])
    assert not ok and "치명" in why
    for ph in ("plan", "idesign"):
        s = {**loop._INIT, "phase": ph, "fix": {}}
        msg = loop.step(s, path=q, act={"plan": lambda s: "기획"}, force=True)
        assert s["phase"] == "develop" and "치명" in msg
    queue.update_item(q, "C-1", stage="done")
    assert o.critical_open(queue.parse(q)) == []


def test_propose_carries_critical(tmp_path, monkeypatch):
    from scripts.audit import propose
    from scripts.autopilot import queue
    monkeypatch.setattr(propose, "PENDING_PATH", tmp_path / "p.md")
    q = tmp_path / "BACKLOG.md"
    q.write_text("", encoding="utf-8")
    f = {"kind": "k1", "verdict": "real", "perspective": "p", "impact": "i", "fix": "x", "critical": True}
    propose.propose([f], q)
    assert queue.parse(q)[0].critical is True
