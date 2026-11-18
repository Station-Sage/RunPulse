"""/api/v1/coach/plan/draft* — 상태·시작·적용 (V2-AI-CLAUDE-QUEUE E5-c)."""
import sqlite3
from datetime import date, timedelta

import pytest
from flask import Flask

from src.db_setup import create_tables, migrate_db
from src.services.plan_replan_service import next_monday
from src.training.goals import add_goal

MON = next_monday(date.today())
RACE = (MON + timedelta(weeks=8, days=5)).isoformat()
H = {"Origin": "http://localhost"}


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
    import src.api.routes_plan_draft as d
    import src.api.routes_plan_replan as r
    monkeypatch.setattr(d, "db_path", lambda: f)
    monkeypatch.setattr(r, "db_path", lambda: f)
    app = Flask(__name__)
    from src.api import api_bp
    app.register_blueprint(api_bp)
    return app.test_client()


def test_state_none_and_availability(client, monkeypatch):
    import src.api.routes_plan_draft as d
    monkeypatch.setattr(d.pcq, "available", lambda conn, cfg: False)
    data = client.get("/api/v1/coach/plan/draft").get_json()["data"]
    assert data["available"] is False and data["state"] == "none" and data["running"] is False


def test_start_unavailable_409(client, monkeypatch):
    import src.api.routes_plan_draft as d
    monkeypatch.setattr(d.pcq, "available", lambda conn, cfg: False)
    r = client.post("/api/v1/coach/plan/draft", json={}, headers=H)
    assert r.status_code == 409 and r.get_json()["error"]["code"] == "UNAVAILABLE"


def test_start_202(client, monkeypatch):
    import src.api.routes_plan_draft as d
    seen = {}
    monkeypatch.setattr(d.pcq, "available", lambda conn, cfg: True)
    monkeypatch.setattr(d.pd, "start_background", lambda p, cfg, params: seen.update(params=params) or True)
    r = client.post("/api/v1/coach/plan/draft", json={"recent_weekly_km": 20}, headers=H)
    assert r.status_code == 202 and r.get_json()["data"] == {"started": True, "running": True}
    assert seen["params"] == {"recent_weekly_km": 20}


def test_apply_requires_anchor_and_no_draft(client):
    assert client.post("/api/v1/coach/plan/draft/apply", json={}, headers=H).status_code == 400
    r = client.post("/api/v1/coach/plan/draft/apply", json={"expect_anchor": MON.isoformat()}, headers=H)
    assert r.status_code == 404 and r.get_json()["error"]["code"] == "NO_DRAFT"
