import json

from scripts.audit import decisions, idesign, loop, release_plan, stopreason, versioning
from scripts.autopilot import queue

PLAN = {"current": "v1", "versions": {
    "v1": {"status": "active", "initiatives": {release_plan.MAINT: {"status": "approved", "items": []}}},
    "v2": {"status": "planned", "initiatives": {"INI-a": {"title": "A", "goal": "g", "verify": ["pytest -q"], "status": "proposed", "items": []}}}}}


def _plan(tmp_path):
    p = tmp_path / "plan.json"
    release_plan.save(json.loads(json.dumps(PLAN)), p)
    return p


def test_set_doc_status(tmp_path):
    d = tmp_path / "PLAN.md"
    d.write_text("---\nstatus: proposed\n---\nx", encoding="utf-8")
    versioning.set_doc_status(d, "approved")
    assert "status: approved" in d.read_text(encoding="utf-8")
    versioning.set_doc_status(tmp_path / "none.md", "approved")


def test_approve_switches_current(tmp_path):
    plan = json.loads(json.dumps(PLAN))
    assert versioning.approve("v2", plan, tmp_path) == ["INI-a"]
    assert plan["current"] == "v2" and plan["versions"]["v1"]["status"] == "closed"
    assert plan["versions"]["v2"]["initiatives"]["INI-a"]["status"] == "approved"


def _rec(choice, status="chosen"):
    return {"id": "VER-v2", "kind": "initiative", "status": status, "choice": choice}


def test_apply_choice_a_b_redo(tmp_path):
    pp, dp = _plan(tmp_path), tmp_path / "d.json"
    decisions.save([_rec("A")], dp)
    st = {"phase": "plan", "stop_reason": stopreason.AWAIT_DECISION, "fails": 2}
    assert "승인" in versioning.apply_choice(_rec("A"), st, dpath=dp, plan_path=pp, releases=tmp_path)
    assert st["phase"] == "idesign" and st["stop_reason"] is None and release_plan.load(pp)["current"] == "v2"
    decisions.save([_rec("B")], dp)
    st = {"phase": "plan", "stop_reason": stopreason.AWAIT_DECISION}
    assert "보류" in versioning.apply_choice(_rec("B"), st, dpath=dp, plan_path=pp)
    assert st["stop_reason"] == stopreason.AWAIT_DECISION
    decisions.save([_rec(None, "redo")], dp)
    versioning.apply_choice(_rec(None, "redo"), st, dpath=dp, plan_path=pp)
    assert st["phase"] == "plan" and decisions.load(dp) == []


GOOD = json.dumps({"design": "접근", "items": [{"text": "t1", "scope": ["src/a.py"], "verify": ["pytest tests/a"]},
                                             {"text": "bad", "scope": ["../x"], "verify": ["v"]}]})


def test_parse_guards():
    body, items = idesign.parse(GOOD)
    assert body == "접근" and [i["text"] for i in items] == ["t1"]
    assert idesign.parse("not json") == ("", [])


def test_design_step_writes_doc_and_items(tmp_path):
    pp, q, rel = _plan(tmp_path), tmp_path / "BACKLOG.md", tmp_path / "rel"
    q.write_text("", encoding="utf-8")
    plan = release_plan.load(pp)
    versioning.approve("v2", plan, rel)
    release_plan.save(plan, pp)
    st = dict(loop._INIT, phase="idesign")
    msg = idesign.design_step(st, ask=lambda *a, **k: GOOD, plan_path=pp, qpath=q, releases=rel)
    assert "1건" in msg
    doc = (rel / "v2" / "initiatives" / "INI-a" / "DESIGN.md").read_text(encoding="utf-8")
    assert "status: designed" in doc
    items = queue.parse(q)
    assert len(items) == 1 and items[0].stage == "queued"
    after = release_plan.load(pp)
    assert release_plan.initiatives(after)["INI-a"]["status"] == "designed" and len(release_plan.initiatives(after)["INI-a"]["items"]) == 1
    assert "없음" in idesign.design_step(st, plan_path=pp, qpath=q, releases=rel) and st["phase"] == "audit"


def test_design_step_fails_without_valid_items(tmp_path):
    pp, q = _plan(tmp_path), tmp_path / "BACKLOG.md"
    q.write_text("", encoding="utf-8")
    plan = release_plan.load(pp)
    versioning.approve("v2", plan, tmp_path)
    release_plan.save(plan, pp)
    st = dict(loop._INIT, phase="idesign")
    assert "실패" in idesign.design_step(st, ask=lambda *a, **k: "{}", plan_path=pp, qpath=q, releases=tmp_path) and st["fails"] == 1


def test_loop_idesign_branch_goes_develop(tmp_path, monkeypatch):
    pp, q = _plan(tmp_path), tmp_path / "BACKLOG.md"
    q.write_text("", encoding="utf-8")
    plan = release_plan.load(pp)
    versioning.approve("v2", plan, tmp_path)
    release_plan.save(plan, pp)
    monkeypatch.setattr(release_plan, "PLAN_PATH", pp)
    st = dict(loop._INIT, phase="idesign")
    loop.step(st, path=q, act={"idesign": {"ask": lambda *a, **k: GOOD, "plan_path": pp, "qpath": q, "releases": tmp_path}})
    assert st["phase"] == "develop"


def test_server_choose_initiative_applies(tmp_path, monkeypatch):
    from scripts.console import server
    pp, dp, sp = _plan(tmp_path), tmp_path / "d.json", tmp_path / "state.json"
    decisions.save([{"id": "VER-v2", "kind": "initiative", "status": "open", "summary": "", "why": "", "options": [{"key": "A", "name": "a"}]}], dp)
    monkeypatch.setattr(server.control, "audit", lambda *a, **k: None)
    r = server.choose("VER-v2", "A", dp, sp, pp)
    assert r["ok"] and "승인" in r["note"]
    assert loop.load_state(sp)["phase"] == "idesign" and release_plan.load(pp)["current"] == "v2"
