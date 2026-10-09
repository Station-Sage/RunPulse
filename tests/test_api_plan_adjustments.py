"""POST/GET /api/v1/coach/plan/adjustments* — 수락·되돌리기·충돌·이력."""
import sqlite3
from datetime import date

import pytest
from flask import Flask

from src.db_setup import create_tables, migrate_db

TODAY = date.today().isoformat()


@pytest.fixture
def client(tmp_path, monkeypatch):
    f = tmp_path / "running.db"
    c = sqlite3.connect(str(f))
    create_tables(c)
    migrate_db(c)
    c.execute("INSERT INTO planned_workouts(id,date,workout_type,distance_km,source) VALUES (7,?,'easy',10.0,'planner')", (TODAY,))
    c.execute("INSERT INTO plan_adjustments(goal_id,workout_id,date,source,op,before_json,after_json,rule_version)"
              " VALUES (1,7,?,'crs','replace','{\"workout_type\":\"easy\",\"distance_km\":10.0}',"
              "'{\"workout_type\":\"easy\",\"distance_km\":10.0}','adjuster_v1')", (TODAY,))
    c.commit()
    c.close()
    import src.api.routes_plan_adjust as m
    monkeypatch.setattr(m, "db_path", lambda: f)
    app = Flask(__name__)
    from src.api import api_bp
    app.register_blueprint(api_bp)
    return app.test_client()


def test_accept_then_revert(client):
    r = client.post("/api/v1/coach/plan/adjustments/1/accept", json={"rev": 1, "via": "plan"})
    assert r.status_code == 200
    d = r.get_json()["data"]
    assert d["adjustment"]["state"] == "accepted" and "week_planned_km" in d and "sessions" in d["compliance"]
    r = client.post("/api/v1/coach/plan/adjustments/1/revert", json={"via": "plan"})
    assert r.get_json()["data"]["adjustment"]["state"] == "undone"


def test_rev_mismatch_is_409(client):
    r = client.post("/api/v1/coach/plan/adjustments/1/accept", json={"rev": 9})
    e = r.get_json()["error"]
    assert r.status_code == 409 and e["code"] == "CONFLICT" and e["details"]["reason"] == "REV_MISMATCH"


def test_not_found_and_bad_request(client):
    assert client.post("/api/v1/coach/plan/adjustments/99/accept", json={"rev": 1}).status_code == 404
    assert client.post("/api/v1/coach/plan/adjustments/1/accept", json={}).status_code == 400


def test_list(client):
    r = client.get(f"/api/v1/coach/plan/1/adjustments?from={TODAY}&to={TODAY}")
    assert r.status_code == 200 and r.get_json()["data"]["adjustments"][0]["state"] == "proposed"
    assert client.get("/api/v1/coach/plan/1/adjustments").status_code == 400


def test_workout_action(client):
    r = client.post("/api/v1/coach/plan/workouts/7/action", json={"op": "reduce", "pct": 30, "via": "plan"})
    assert r.status_code == 201
    d = r.get_json()["data"]
    assert d["adjustment"]["state"] == "accepted" and d["adjustment"]["after"]["distance_km"] == 7.0
    assert "compliance" in d and d["week_planned_km"]["after"] <= d["week_planned_km"]["before"]
    assert client.post(f"/api/v1/coach/plan/adjustments/{d['adjustment']['id']}/revert", json={}).status_code == 200


def test_workout_action_errors(client):
    p = "/api/v1/coach/plan/workouts/"
    assert client.post(p + "7/action", json={"op": "reduce", "pct": 0}).status_code == 400
    assert client.post(p + "7/action", json={"op": "move", "to_date": "2030-01-01"}).status_code == 409
    assert client.post(p + "7/action", json={"op": "move"}).status_code == 400
    assert client.post(p + "99/action", json={"op": "rest"}).status_code == 404
