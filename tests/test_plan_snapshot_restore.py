"""PLN-43 — 교체 시 스냅샷 저장, 복원 시 write_planner_rows 로 goal_id 와 함께 재삽입, 복원 후보 목록."""
from __future__ import annotations

import json
import sqlite3
from datetime import date, timedelta

from flask import Flask

from src.db_setup import create_tables, migrate_db
from src.services import plan_restore

H = {"Origin": "http://localhost"}
RACE = (date.today() + timedelta(weeks=12)).isoformat()
BODY = {"distance_km": 21.0975, "race_date": RACE, "weeks": 8, "name": "snap", "run_weekdays": [0, 2, 4, 6]}


def _client(tmp_path):
    db = tmp_path / "running.db"
    c = sqlite3.connect(str(db))
    create_tables(c)
    migrate_db(c)
    c.close()
    import src.api.routes_plan as rp
    rp.db_path = lambda: db
    app = Flask(__name__)
    app.config["TESTING"] = True
    from src.api import api_bp
    app.register_blueprint(api_bp)
    return app.test_client(), db


def test_replace_stores_snapshot_and_restore_reinserts_with_goal_id(tmp_path):
    cl, db = _client(tmp_path)
    g1 = cl.post("/api/v1/coach/plan", json={**BODY, "expect_active_goal_id": None}, headers=H).get_json()["data"]["goal_id"]
    g2 = cl.post("/api/v1/coach/plan", json={**BODY, "expect_active_goal_id": g1}, headers=H).get_json()["data"]["goal_id"]
    c = sqlite3.connect(str(db))
    snap = json.loads(c.execute("SELECT plan_snapshot_json FROM goals WHERE id=?", (g1,)).fetchone()[0])
    assert snap and all(r["date"] >= date.today().isoformat() for r in snap)
    assert c.execute("SELECT COUNT(*) FROM planned_workouts WHERE goal_id=?", (g1,)).fetchone()[0] == 0
    lst = cl.get("/api/v1/coach/plan/restorable").get_json()["data"]["plans"]
    assert [p["goal_id"] for p in lst] == [g1] and lst[0]["rows"] == len(snap)
    out = cl.post(f"/api/v1/coach/plan/{g1}/restore", json={"expect_active_goal_id": g2}, headers=H).get_json()["data"]
    assert out["restored"] > 0
    assert c.execute("SELECT COUNT(*) FROM planned_workouts WHERE goal_id=?", (g1,)).fetchone()[0] == out["restored"]
    assert c.execute("SELECT plan_snapshot_json FROM goals WHERE id=?", (g1,)).fetchone()[0] is None
    assert [p["goal_id"] for p in cl.get("/api/v1/coach/plan/restorable").get_json()["data"]["plans"]] == [g2]


def test_list_restorable_skips_empty_and_bad_json():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    migrate_db(c)
    for i, blob in enumerate([None, "not-json", "[]"]):
        c.execute("INSERT INTO goals(name, race_date, distance_km, status, plan_snapshot_json) VALUES (?,?,?,?,?)",
                  (f"g{i}", "2027-01-01", 10.0, "cancelled", blob))
    assert [p["rows"] for p in plan_restore.list_restorable(c)] == [0]
