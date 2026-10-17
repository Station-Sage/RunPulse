"""R2 API — 활성 플랜 교체 409 확인 흐름, 복원 라우트, 비활성 플랜 재계획 undo 차단."""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

import pytest
from flask import Flask

from src.db_setup import create_tables, migrate_db

H = {"Origin": "http://localhost"}
RACE = (date.today() + timedelta(weeks=12)).isoformat()
BODY = {"distance_km": 21.0975, "race_date": RACE, "weeks": 8, "name": "r2", "run_weekdays": [0, 2, 4, 6]}


@pytest.fixture
def api(tmp_path):
    db = tmp_path / "running.db"
    c = sqlite3.connect(str(db))
    create_tables(c)
    migrate_db(c)
    c.close()
    import src.api.routes_plan as rp
    orig = rp.db_path
    rp.db_path = lambda: db
    app = Flask(__name__)
    app.config["TESTING"] = True
    from src.api import api_bp
    app.register_blueprint(api_bp)
    with app.test_client() as cl:
        yield cl, db
    rp.db_path = orig


def test_409_then_confirm_replaces_and_restore_swaps(api):
    cl, db = api
    r1 = cl.post("/api/v1/coach/plan", json={**BODY, "expect_active_goal_id": None}, headers=H)
    assert r1.status_code == 200
    g1 = r1.get_json()["data"]["goal_id"]
    r2 = cl.post("/api/v1/coach/plan", json={**BODY, "expect_active_goal_id": None}, headers=H)
    assert r2.status_code == 409 and r2.get_json()["error"]["code"] == "ACTIVE_PLAN_EXISTS"
    r3 = cl.post("/api/v1/coach/plan", json={**BODY, "expect_active_goal_id": g1}, headers=H)
    assert r3.status_code == 200
    g2 = r3.get_json()["data"]["goal_id"]
    r4 = cl.post(f"/api/v1/coach/plan/{g1}/restore", json={"expect_active_goal_id": None}, headers=H)
    assert r4.status_code == 409
    r5 = cl.post(f"/api/v1/coach/plan/{g1}/restore", json={"expect_active_goal_id": g2}, headers=H)
    assert r5.status_code == 200 and r5.get_json()["data"]["goal_id"] == g1
    c = sqlite3.connect(str(db))
    assert dict(c.execute("SELECT id, status FROM goals").fetchall()) == {g1: "active", g2: "cancelled"}
    assert cl.post("/api/v1/coach/plan/9999/restore", json={}, headers=H).status_code == 404


def test_undo_blocked_for_non_active_goal(api):
    from src.services.plan_replan_service import _undo_blocker
    _, db = api
    c = sqlite3.connect(str(db))
    c.execute("INSERT INTO goals(name, distance_km, race_date, status) VALUES ('x', 10, '2030-01-01', 'cancelled')")
    gid = c.execute("SELECT MAX(id) FROM goals").fetchone()[0]
    c.execute("INSERT INTO plan_replans(goal_id, anchor_monday, start_km, start_source) VALUES (?, '2030-01-07', 30, 'user')", (gid,))
    rid = c.execute("SELECT MAX(id) FROM plan_replans").fetchone()[0]
    assert "활성이 아닌" in _undo_blocker(c, rid, date.today())


def test_weeks_route(api):
    cl, _ = api
    gid = cl.post("/api/v1/coach/plan", json={**BODY, "expect_active_goal_id": None}, headers=H).get_json()["data"]["goal_id"]
    d = cl.get(f"/api/v1/coach/plan/{gid}/weeks").get_json()["data"]
    assert d["weeks"] and d["basis"]["scope"] == "week"
    assert cl.get("/api/v1/coach/plan/9999/weeks").status_code == 404
