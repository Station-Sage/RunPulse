"""/api/v1/coach/plan/replan* — 200/400/404/409/503 (ADR-035 부록 R)."""
import sqlite3
from datetime import timedelta

import pytest
from flask import Flask

from src.db_setup import create_tables, migrate_db
from src.services.plan_replan_service import next_monday
from src.training.goals import add_goal
from datetime import date

MON = next_monday(date.today())
RACE = (MON + timedelta(weeks=8, days=5)).isoformat()


def _app(f, monkeypatch):
    import src.api.routes_plan_replan as m
    monkeypatch.setattr(m, "db_path", lambda: f)
    app = Flask(__name__)
    from src.api import api_bp
    app.register_blueprint(api_bp)
    return app.test_client()


@pytest.fixture
def client(tmp_path, monkeypatch):
    f = tmp_path / "running.db"
    c = sqlite3.connect(str(f))
    create_tables(c)
    migrate_db(c)
    gid = add_goal(c, "g", 21.0975, RACE, None, rules_version=2)
    c.execute("UPDATE goals SET plan_weeks=12, distance_label='half' WHERE id=?", (gid,))
    c.commit()
    c.close()
    return _app(f, monkeypatch)


def test_preview_apply_undo(client):
    r = client.get("/api/v1/coach/plan/replan/preview?recent_weekly_km=20")
    assert r.status_code == 200 and r.get_json()["data"]["anchor_monday"] == MON.isoformat()
    r = client.post("/api/v1/coach/plan/replan", json={"recent_weekly_km": 20, "expect_anchor": MON.isoformat()})
    assert r.status_code == 200
    rid = r.get_json()["data"]["replan_id"]
    assert client.post(f"/api/v1/coach/plan/replan/{rid}/undo").status_code == 200
    assert client.post(f"/api/v1/coach/plan/replan/{rid}/undo").status_code == 409


def test_bad_request_and_conflict(client):
    assert client.get("/api/v1/coach/plan/replan/preview?recent_weekly_km=abc").status_code == 400
    assert client.post("/api/v1/coach/plan/replan", json={}).status_code == 400
    assert client.post("/api/v1/coach/plan/replan", json={"expect_anchor": "2000-01-03"}).status_code == 409


def test_no_goal_404_and_no_db_503(tmp_path, monkeypatch):
    f = tmp_path / "running.db"
    c = sqlite3.connect(str(f))
    create_tables(c)
    migrate_db(c)
    c.close()
    assert _app(f, monkeypatch).get("/api/v1/coach/plan/replan/preview").status_code == 404
    assert _app(tmp_path / "none.db", monkeypatch).get("/api/v1/coach/plan/replan/preview").status_code == 503
