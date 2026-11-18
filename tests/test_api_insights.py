"""GET/POST /api/v1/insights* + 체크인 훅 (V2-REPAIR D2)."""
from __future__ import annotations

import sqlite3

import pytest
from flask import Flask

from src.db_setup import create_tables, migrate_db

H = {"Origin": "http://localhost"}


@pytest.fixture
def ctx(tmp_path, monkeypatch):
    db_file = tmp_path / "running.db"
    conn = sqlite3.connect(str(db_file))
    create_tables(conn)
    migrate_db(conn)
    conn.execute(
        "INSERT INTO insight_events(kind,severity,as_of,dedupe_key,signals_json,text,action_json) "
        "VALUES('load_spike','watch','2026-11-18','load_spike:acwr','[]','부하 급증','{\"label\":\"x\",\"route\":\"/today\"}')")
    conn.commit()
    conn.close()
    import src.api.routes_insights as ri
    import src.api.routes_today as rt
    import src.utils.user_context as uc
    for mod in (ri, rt, uc):
        monkeypatch.setattr(mod, "db_path", lambda: db_file)
    app = Flask(__name__)
    app.config["TESTING"] = True
    from src.api import api_bp
    app.register_blueprint(api_bp)
    with app.test_client() as c:
        yield c, db_file


def test_list_open(ctx):
    c, _ = ctx
    ev = c.get("/api/v1/insights").get_json()["data"]["events"]
    assert len(ev) == 1 and ev[0]["action"]["route"] == "/today"


def test_invalid_state(ctx):
    assert ctx[0].get("/api/v1/insights?state=zzz").status_code == 400


def test_seen_then_dismiss(ctx):
    c, _ = ctx
    assert c.post("/api/v1/insights/1/seen", headers=H).status_code == 200
    assert c.post("/api/v1/insights/1/seen", headers=H).status_code == 404
    assert c.post("/api/v1/insights/1/dismiss", headers=H).status_code == 200
    assert c.get("/api/v1/insights").get_json()["data"]["events"] == []
    assert c.post("/api/v1/insights/99/dismiss", headers=H).status_code == 404


def test_checkin_hook_creates_pain_event(ctx):
    c, db = ctx
    assert c.post("/api/v1/today/checkin", json={"fatigue": 5, "pain": "severe"}, headers=H).status_code == 200
    kinds = [e["kind"] for e in c.get("/api/v1/insights").get_json()["data"]["events"]]
    assert "pain_flag" in kinds
