from scripts.audit import release_plan as rp

BL = """- **[AUD-aaaaaa]** a
  <!-- autopilot: {"stage":"done","mode":"auto","attempts":0,"deps":[]} -->
- **[AUD-bbbbbb]** b
  <!-- autopilot: {"stage":"queued","mode":"auto","attempts":0,"deps":[]} -->
- **[X-1]** manual
"""


def test_load_default_and_roundtrip(tmp_path):
    p = tmp_path / "plan.json"
    plan = rp.load(p)
    assert rp.current(plan) == "v1" and rp.MAINT in rp.initiatives(plan)
    rp.save(plan, p)
    assert rp.load(p) == plan


def test_link_idempotent():
    plan = {"current": "v1", "versions": {"v1": {"initiatives": {"A": {"items": []}, "B": {"items": []}}}}}
    assert rp.link(plan, "A", "AUD-1") is True
    assert rp.link(plan, "B", "AUD-1") is False
    assert rp.linked_ids(plan) == {"AUD-1"}


def test_sync_maint_links_only_unlinked_aud(tmp_path):
    q = tmp_path / "BACKLOG.md"
    q.write_text(BL, encoding="utf-8")
    plan = {"current": "v1", "versions": {"v1": {"initiatives": {"INI-NEW": {"items": ["AUD-aaaaaa"]}}}}}
    assert rp.sync_maint(plan, q) == ["AUD-bbbbbb"]
    assert plan["versions"]["v1"]["initiatives"][rp.MAINT]["items"] == ["AUD-bbbbbb"]
    assert rp.sync_maint(plan, q) == []


def test_rollup_counts(tmp_path):
    q = tmp_path / "BACKLOG.md"
    q.write_text(BL, encoding="utf-8")
    plan = {"current": "v1", "versions": {"v1": {"title": "t", "initiatives": {"I": {"items": ["AUD-aaaaaa", "AUD-bbbbbb", "AUD-zz"]}}}}}
    r = rp.rollup(plan, q)
    ini = r["initiatives"][0]
    assert (r["version"], ini["total"], ini["done"]) == ("v1", 3, 1)
    assert ini["by_stage"] == {"done": 1, "queued": 1, "missing": 1}


def test_rollup_phases_active_and_goal(tmp_path):
    q = tmp_path / "BACKLOG.md"
    q.write_text(BL, encoding="utf-8")
    plan = {"current": "v2", "versions": {"v2": {"title": "t", "goal": "G", "phases": [
        {"id": "I", "title": "a", "initiatives": ["A"]}, {"id": "II", "title": "b", "initiatives": ["B"]}],
        "initiatives": {"A": {"items": ["AUD-aaaaaa"]}, "B": {"items": ["AUD-bbbbbb"]}}}}}
    r = rp.rollup(plan, q)
    assert r["goal"] == "G"
    assert [(p["id"], p["done"], p["total"], p["active"]) for p in r["phases"]] == [("I", 1, 1, False), ("II", 0, 1, True)]
