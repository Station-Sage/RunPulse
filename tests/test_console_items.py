"""개발 항목 목록·상세(items) + 라우팅."""
import json

from scripts.console import items, server

Q = ('- **[A-1]** 첫째\n  <!-- autopilot: {"stage":"done","mode":"auto","attempts":2,"deps":[]} -->\n'
     '- **[A-2]** 둘째\n  <!-- autopilot: {"stage":"review","mode":"auto","attempts":1,"deps":[],"verify":["pytest -q"]} -->\n'
     '- **[A-3]** 셋째\n  <!-- autopilot: {"stage":"queued","mode":"auto","attempts":0,"deps":[]} -->\n')


def test_item_list_groups_and_counts(tmp_path):
    q = tmp_path / "B.md"
    q.write_text(Q, encoding="utf-8")
    r = items.item_list(q)
    assert r["total"] == 3 and r["counts"]["done"] == 1 and r["done_pct"] == 33
    assert [i["id"] for i in r["items"]] == ["A-3", "A-2", "A-1"]


def test_item_detail_review_and_report(tmp_path):
    q = tmp_path / "B.md"
    q.write_text(Q, encoding="utf-8")
    logs = tmp_path / "runs"
    logs.mkdir()
    (logs / "20260101_A-2.jsonl").write_text(json.dumps({"type": "result", "result": "보고 본문"}) + "\n", encoding="utf-8")
    d = items.item_detail("A-2", q, tmp_path / "d.json", logs,
                          [{"unit_id": "A-2", "ts": 1, "outcome": "success", "cost_usd": 1.0}],
                          [{"ts": 1, "kind": "unit_start", "unit": "A-2"}], tmp_path)
    assert d["item"]["stage"] == "review" and d["report"]["report"] == "보고 본문"
    assert d["runs"][0]["outcome"] == "success" and d["timeline"][0]["kind"] == "unit_start"
    assert d["review"]["verify_cmds"] == ["pytest -q"] and d["review"]["how"]
    assert items.item_detail("NOPE", q, tmp_path / "d.json", logs, [], [], tmp_path) is None


def test_routes(tmp_path, monkeypatch):
    q = tmp_path / "B.md"
    q.write_text(Q, encoding="utf-8")
    monkeypatch.setattr(items.settings, "QUEUE_PATH", q)
    monkeypatch.setattr(items.settings, "RUN_LOG_DIR", tmp_path / "runs")
    monkeypatch.setattr(items.settings, "STATE_DIR", tmp_path)
    monkeypatch.setattr(items.ledger, "read_all", lambda: [])
    monkeypatch.setattr(items.progress, "read_events", lambda: [])
    monkeypatch.setattr(items.decisions, "load", lambda p=None: [])
    assert server.route("GET", "/api/items")[1]["total"] == 3
    assert server.route("GET", "/api/item/A-1")[0] == 200
    assert server.route("GET", "/api/item/ZZ")[0] == 404


def _facts(h_commit="h1"):
    return {"A-2": h_commit}, {"h1"}


def test_pipeline_steps_from_stage_ledger_and_git(tmp_path):
    from scripts.autopilot import queue
    q = tmp_path / "B.md"
    q.write_text(Q, encoding="utf-8")
    its = queue.parse(q)
    p = items.pipeline(its, [{"unit_id": "A-2", "outcome": "success"}], {}, _facts())
    assert p["A-1"]["steps"] == dict(design=True, develop=True, test=True, commit=True, deploy=True)
    assert p["A-2"]["steps"] == dict(design=True, develop=True, test=True, commit=True, deploy=True)
    assert p["A-3"]["steps"] == dict(design=True, develop=False, test=False, commit=False, deploy=False)
    assert not p["A-3"]["running"]
    p2 = items.pipeline(its, [], {"phase": "develop", "unit": "A-3", "stop_reason": None}, ({}, set()))
    assert p2["A-3"]["running"] and not p2["A-2"]["steps"]["commit"]


def test_git_facts_parses_ids_and_base():
    def fake(args):
        return "h1\tfeat(autopilot): x (A-2)\nh2\tdocs: none" if args[0] == "log" else "h1 h9"
    commits, base = items.git_facts(fake)
    assert commits.get("A-2") == "h1" and "h1" in base


def test_done_items_sorted_by_recent_completion(tmp_path):
    q = tmp_path / "B.md"
    done = '  <!-- autopilot: {"stage":"done","mode":"auto","attempts":1,"deps":[]} -->\n'
    q.write_text("".join(f"- **[{i}]** x\n{done}" for i in ("D-1", "D-2", "D-3")), encoding="utf-8")
    ents = [{"unit_id": "D-1", "ts": 300, "outcome": "success"}, {"unit_id": "D-2", "ts": 100, "outcome": "success"}]
    r = items.item_list(q, ents, {}, ({}, set()), times={"D-3": 200})
    assert [i["id"] for i in r["items"]] == ["D-1", "D-3", "D-2"]
    assert r["items"][0]["done_at"] == 300
