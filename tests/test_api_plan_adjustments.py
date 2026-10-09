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


def test_workout_action_easy_and_reps(client):
    import json
    import sqlite3 as sq
    import src.api.routes_plan_adjust as m
    c = sq.connect(str(m.db_path()))
    c.execute("UPDATE planned_workouts SET workout_type='interval', interval_prescription=? WHERE id=7",
              (json.dumps({"sets": 6, "rep_m": 1000, "interval_pace": 270}),))
    c.commit()
    c.close()
    p = "/api/v1/coach/plan/workouts/7/action"
    r = client.post(p, json={"op": "reduce", "reps": 1})
    assert r.status_code == 201 and r.get_json()["data"]["adjustment"]["after"]["distance_km"] == 9.0
    r = client.post(p, json={"op": "easy"})
    assert r.status_code == 201 and r.get_json()["data"]["adjustment"]["after"]["workout_type"] == "easy"


def test_preview_and_load_delta_field(client):
    p = "/api/v1/coach/plan/workouts/7/action/preview"
    r = client.get(p + "?op=reduce&pct=30")
    assert r.status_code == 200 and "load_delta" in r.get_json()["data"]
    assert client.get(p + "?op=reduce&pct=x").status_code == 400
    assert client.get(p + "?op=bogus").status_code == 400
    assert client.get("/api/v1/coach/plan/workouts/99/action/preview?op=rest").status_code == 404
    r = client.post("/api/v1/coach/plan/workouts/7/action", json={"op": "rest"})
    assert r.status_code == 201 and "load_delta" in r.get_json()["data"]


def test_pain_levels_force_rest_and_validate(client):
    p = "/api/v1/coach/plan/workouts/7/action"
    assert client.post(p, json={"op": "reduce", "pct": 30, "reason": "pain"}).status_code == 400
    assert client.post(p, json={"op": "reduce", "pct": 30, "reason": "pain", "pain_level": "mild",
                                "pain_sites": ["foot", "knee", "hip", "calf"]}).status_code == 400
    r = client.post(p, json={"op": "reduce", "pct": 30, "reason": "pain", "pain_level": "moderate",
                             "pain_sites": ["knee"]})
    d = r.get_json()["data"]
    assert r.status_code == 201 and d["adjustment"]["after"]["workout_type"] == "rest"
    assert d["adjustment"]["reasons"] == [{"key": "pain", "level": "moderate", "sites": ["knee"]}]
    assert client.post(p, json={"op": "move", "to_date": "2030-01-01", "reason": "pain"}).status_code == 409


def test_preview_accepts_pain_sites_csv(client):
    p = "/api/v1/coach/plan/workouts/7/action/preview"
    assert client.get(p + "?op=reduce&pct=30&reason=pain&pain_level=moderate&pain_sites=knee,foot").status_code == 200
    assert client.get(p + "?op=reduce&pct=30&reason=pain&pain_level=bogus&pain_sites=knee").status_code == 400


def _seed_replan(client, pain=False):
    import json
    import sqlite3 as sq
    from datetime import timedelta
    import src.api.routes_plan_adjust as m
    c = sq.connect(str(m.db_path()))
    c.execute("INSERT INTO goals(id,name,race_date,distance_km,target_time_sec,status) VALUES (1,'m','2099-01-01',42.195,12600,'active')")
    ws = date.today() - timedelta(days=date.today().weekday())
    for k in (1, 2):
        for i in range(2):
            d = (ws - timedelta(weeks=k) + timedelta(days=i)).isoformat()
            c.execute("INSERT INTO planned_workouts(date,workout_type,distance_km,source) VALUES (?, 'easy', 8.0,'planner')", (d,))
    if pain:
        c.execute("INSERT INTO plan_adjustments(goal_id,workout_id,date,source,op,before_json,after_json,reasons_json,rule_version,decision)"
                  " VALUES (1,7,?,'user','rest','{\"workout_type\":\"easy\"}','{\"workout_type\":\"rest\"}',?,'t','accepted')",
                  (TODAY, json.dumps([{"key": "pain", "level": "mild", "sites": ["foot"]}])))
    c.commit()
    c.close()


def test_advisories_replan_with_link_and_no_record(client):
    _seed_replan(client)
    r = client.get(f"/api/v1/coach/plan/advisories?date={TODAY}")
    items = r.get_json()["data"]["advisories"]
    rp = [a for a in items if a["code"] == "REPLAN"][0]
    assert rp["link"]["distance_km"] == 42.195 and rp["link"]["target_time_sec"] == 12600
    assert "recent_weekly_km" not in rp["link"]
    again = client.get(f"/api/v1/coach/plan/advisories?date={TODAY}").get_json()["data"]["advisories"]
    assert [a["code"] for a in again] == [a["code"] for a in items]


def test_advisories_suppressed_by_recent_pain_and_errors(client):
    _seed_replan(client, pain=True)
    assert client.get(f"/api/v1/coach/plan/advisories?date={TODAY}").get_json()["data"]["advisories"] == []
    assert client.get("/api/v1/coach/plan/advisories").status_code == 400
