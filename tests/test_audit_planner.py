import json

from scripts.audit import decisions, planner, release_plan, stopreason


def _root(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.py").write_text("x = 1\nfoo_bar()\n", encoding="utf-8")
    return tmp_path


def _ini(**kw):
    d = {"id": "INI-pace", "title": "페이스", "kind": "new", "principle": 2, "question": "왜 느렸나", "goal": "원인 표시",
         "evidence": [{"path": "src/a.py:2", "quote": "foo_bar"}], "verify": ["pytest -q"]}
    d.update(kw)
    return d


def test_next_version():
    assert planner.next_version("v1") == "v2" and planner.next_version("x") == "x-next"


def test_evidence_requires_real_quote_and_inside_root(tmp_path):
    r = _root(tmp_path)
    assert planner.evidence_ok({"path": "src/a.py:2", "quote": "foo_bar"}, r)
    assert not planner.evidence_ok({"path": "src/a.py:1", "quote": "foo_bar"}, r)
    assert not planner.evidence_ok({"path": "../etc/passwd:1", "quote": "root"}, r)
    assert not planner.evidence_ok({"path": "src/a.py:99", "quote": "x"}, r)


def test_valid_initiative_guards(tmp_path):
    r = _root(tmp_path)
    assert planner.valid_initiative(_ini(), r) is None
    assert planner.valid_initiative(_ini(id="bad"), r)
    assert planner.valid_initiative(_ini(principle=9), r)
    assert planner.valid_initiative(_ini(goal="전반적 개선"), r)
    assert planner.valid_initiative(_ini(verify=[]), r)
    assert planner.valid_initiative(_ini(evidence=[]), r)


def test_parse_drops_invalid(tmp_path):
    r = _root(tmp_path)
    txt = json.dumps({"title": "t", "initiatives": [_ini(), _ini(id="INI-bad", goal="다양한")], "gaps": "g"})
    prop, dropped = planner.parse(txt, r)
    assert [i["id"] for i in prop["initiatives"]] == ["INI-pace"] and len(dropped) == 1


def test_plan_writes_doc_state_and_decision(tmp_path):
    r = _root(tmp_path)
    resp = json.dumps({"title": "v2 제목", "initiatives": [_ini()], "gaps": "누락"})
    st, dp, pp = {}, tmp_path / "d.json", tmp_path / "p.json"
    release_plan.save(release_plan.load(tmp_path / "none"), pp)
    msg = planner.plan(st, ask=lambda *a, **k: resp, root=r, dpath=dp, plan_path=pp)
    assert "1건" in msg and st["stop"]["reason"] == stopreason.AWAIT_DECISION if "stop" in st else True
    assert (r / "v0.3" / "data" / "releases" / "v2" / "PLAN.md").exists()
    assert release_plan.load(pp)["versions"]["v2"]["initiatives"]["INI-pace"]["status"] == "proposed"
    rec = decisions.load(dp)[0]
    assert rec["id"] == "VER-v2" and rec["kind"] == "initiative"
    again = planner.plan({}, ask=lambda *a, **k: 1 / 0, root=r, dpath=dp, plan_path=pp)
    assert "대기 중" in again


def test_plan_all_dropped_stops(tmp_path):
    r = _root(tmp_path)
    st = {}
    msg = planner.plan(st, ask=lambda *a, **k: "not json", root=r, dpath=tmp_path / "d.json", plan_path=tmp_path / "p.json")
    assert "0건" in msg and not (tmp_path / "d.json").exists()


def test_phases_assign_orphans_and_drop_unknown():
    from scripts.audit import planner
    out = planner._phases([{"id": "I", "title": "a", "initiatives": ["INI-a", "INI-zz"]}], {"INI-a", "INI-b"})
    assert out == [{"id": "I", "title": "a", "initiatives": ["INI-a", "INI-b"]}]
    assert planner._phases(None, {"INI-a"}) == [{"id": "I", "title": "전체", "initiatives": ["INI-a"]}]


def test_render_plan_and_record_include_goal_phases():
    prop = {"title": "t", "gaps": "", "goal": "G목표", "phases": [{"id": "I", "title": "기반", "initiatives": ["INI-a"]}],
            "initiatives": [{"id": "INI-a", "title": "a", "kind": "new", "principle": 1, "question": "q", "goal": "g",
                             "evidence": [], "verify": ["v"]}]}
    md = planner.render_plan("v2", prop)
    assert "## 제품 목표\nG목표" in md and "- I. 기반: INI-a" in md
    assert "G목표" in planner.decision_record("v2", prop)["summary"]
