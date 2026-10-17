"""RC-c: /api/v1/race-calendar* — CRUD·영향·플랜 반영·복원·되돌리기 + 봉투 오류."""
import sqlite3

import pytest
from flask import Flask

from src.db_setup import create_tables, migrate_db

H = {"Origin": "http://localhost"}
BODY = {"name": "서울", "race_date": "2099-12-06", "distance_km": 42.195, "priority": "B"}


@pytest.fixture
def ctx(tmp_path, monkeypatch):
    f = tmp_path / "running.db"
    c = sqlite3.connect(str(f))
    create_tables(c)
    migrate_db(c)
    c.commit()
    c.close()
    import src.api.routes_race_calendar as m
    monkeypatch.setattr(m, "db_path", lambda: f)
    from src.api import api_bp
    app = Flask(__name__)
    app.register_blueprint(api_bp)
    return app.test_client(), f


def _post(cl, body=None, **kw):
    return cl.post("/api/v1/race-calendar", json={**BODY, **(body or {}), **kw}, headers=H)


def test_create_list_get_patch(ctx):
    cl, _ = ctx
    r = _post(cl)
    assert r.status_code == 201
    d = r.get_json()["data"]
    assert d["status"] == "planned" and d["needs_review"] is False and d["goal_linked"] is False
    rid = d["id"]
    assert _post(cl).status_code == 409
    z = cl.get("/api/v1/race-calendar").get_json()["data"]
    assert z["goal_race_id"] is None and [x["id"] for x in z["upcoming"]] == [rid]
    assert cl.get(f"/api/v1/race-calendar/{rid}").get_json()["data"]["name"] == "서울"
    r = cl.patch(f"/api/v1/race-calendar/{rid}", json={"note": "메모"}, headers=H)
    assert r.status_code == 200 and r.get_json()["data"]["note"] == "메모"
    assert r.get_json()["data"]["priority"] == "B"
    assert cl.get("/api/v1/race-calendar/999").status_code == 404


def test_validation_envelope(ctx):
    cl, _ = ctx
    assert _post(cl, priority="Z").status_code == 400


def test_cancel_goal_linked_needs_confirm(ctx):
    cl, f = ctx
    d = _post(cl, priority="A", goal_type="finish").get_json()["data"]
    c = sqlite3.connect(str(f))
    c.execute("INSERT INTO goals(name, distance_km, race_date, status, race_id) VALUES ('g', 42.195, '2099-12-06', 'active', ?)",
              (d["id"],))
    c.commit()
    c.close()
    assert cl.get(f"/api/v1/race-calendar/{d['id']}").get_json()["data"]["goal_linked"] is True
    r = cl.delete(f"/api/v1/race-calendar/{d['id']}", headers=H)
    assert r.status_code == 409
    e = r.get_json()["error"]
    assert e["code"] == "GOAL_LINKED" and e["details"]["needs_confirm"] is True
    r = cl.delete(f"/api/v1/race-calendar/{d['id']}", json={"cancel_goal": True}, headers=H)
    assert r.status_code == 200 and r.get_json()["data"]["goal_cancelled"] is True
    assert r.get_json()["data"]["status"] == "cancelled"


def test_cancel_plain_via_query(ctx):
    cl, _ = ctx
    rid = _post(cl).get_json()["data"]["id"]
    r = cl.delete(f"/api/v1/race-calendar/{rid}?cancel_goal=1", headers=H)
    assert r.status_code == 200 and r.get_json()["data"]["goal_cancelled"] is False


def _seed_plan(f):
    c = sqlite3.connect(str(f))
    c.execute("INSERT INTO goals(name, distance_km, race_date, status) VALUES ('g', 42.195, '2099-12-06', 'active')")
    gid = c.execute("SELECT id FROM goals").fetchone()[0]
    for day in ("2099-12-03", "2099-12-04"):
        c.execute("INSERT INTO planned_workouts(date, workout_type, distance_km, source, goal_id) "
                  "VALUES (?, 'tempo', 10, 'planner', ?)", (day, gid))
    c.commit()
    c.close()


def test_impact_and_plan_actions(ctx):
    cl, f = ctx
    rid = _post(cl, race_date="2099-12-06").get_json()["data"]["id"]
    imp = cl.get(f"/api/v1/race-calendar/{rid}/impact").get_json()["data"]
    assert imp["n"] == 0
    r = cl.post(f"/api/v1/race-calendar/{rid}/plan", json={"action": "adapt"}, headers=H)
    assert r.status_code == 409 and r.get_json()["error"]["code"] == "NO_ROWS"
    assert cl.post(f"/api/v1/race-calendar/{rid}/plan", json={"action": "undo"}, headers=H).status_code == 409
    assert cl.post(f"/api/v1/race-calendar/{rid}/plan", json={"action": "bad"}, headers=H).status_code == 400

    _seed_plan(f)
    assert cl.get(f"/api/v1/race-calendar/{rid}/impact").get_json()["data"]["n"] > 0
    r = cl.post(f"/api/v1/race-calendar/{rid}/plan", json={"action": "adapt"}, headers=H)
    assert r.status_code == 200
    d = r.get_json()["data"]
    assert d["plan_state"] == "applied" and d["adapt_choice"] == "adapt" and d["plan"]["n"] > 0
    r = cl.post(f"/api/v1/race-calendar/{rid}/plan", json={"action": "undo"}, headers=H)
    assert r.get_json()["data"]["plan_state"] == "none" and r.get_json()["data"]["plan"]["undone"] > 0
    r = cl.post(f"/api/v1/race-calendar/{rid}/plan", json={"action": "no_adapt"}, headers=H)
    assert r.get_json()["data"]["adapt_choice"] == "no_adapt"
    r = cl.post(f"/api/v1/race-calendar/{rid}/plan", json={"action": "later"}, headers=H)
    assert r.get_json()["data"]["adapt_choice"] == "later"


def test_restore_and_conflicts(ctx):
    cl, _ = ctx
    assert cl.post("/api/v1/race-calendar/999/restore", json={}, headers=H).status_code == 404
    past = _post(cl, race_date="2020-01-01", name="옛날").get_json()["data"]["id"]
    cl.delete(f"/api/v1/race-calendar/{past}", headers=H)
    r = cl.post(f"/api/v1/race-calendar/{past}/restore", json={}, headers=H)
    assert r.status_code == 409 and r.get_json()["error"]["code"] == "CONFIRM_PAST"
    r = cl.post(f"/api/v1/race-calendar/{past}/restore", json={"confirm_past": True}, headers=H)
    assert r.status_code == 200 and r.get_json()["data"]["status"] == "done"
    assert "restore" in r.get_json()["data"]
    assert cl.post(f"/api/v1/race-calendar/{past}/restore", json={}, headers=H).get_json()["error"]["code"] == "NOT_CANCELLED"


def test_restore_a_conflict_and_reopen(ctx):
    cl, _ = ctx
    a1 = _post(cl, priority="A", name="A1", race_date="2099-11-01", distance_km=21.1).get_json()["data"]["id"]
    cl.delete(f"/api/v1/race-calendar/{a1}", headers=H)
    _post(cl, priority="A", name="A2", race_date="2099-12-06")
    r = cl.post(f"/api/v1/race-calendar/{a1}/restore", json={}, headers=H)
    assert r.status_code == 409 and r.get_json()["error"]["code"] == "A_CONFLICT"
    r = cl.post(f"/api/v1/race-calendar/{a1}/restore", json={"demote_existing_a": True}, headers=H)
    assert r.status_code == 200 and r.get_json()["data"]["status"] == "planned"
    r = cl.post(f"/api/v1/race-calendar/{a1}/reopen", json={}, headers=H)
    assert r.status_code == 409 and r.get_json()["error"]["code"] == "NOT_NEEDS_REVIEW"


def test_reopen_needs_review(ctx):
    cl, f = ctx
    rid = _post(cl).get_json()["data"]["id"]
    c = sqlite3.connect(str(f))
    c.execute("UPDATE race_calendar SET status='done' WHERE id=?", (rid,))
    c.commit()
    c.close()
    d = cl.get(f"/api/v1/race-calendar/{rid}").get_json()["data"]
    assert d["needs_review"] is True
    r = cl.post(f"/api/v1/race-calendar/{rid}/reopen", json={}, headers=H)
    assert r.status_code == 200 and r.get_json()["data"]["status"] == "planned"
