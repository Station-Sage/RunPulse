"""tests/test_api_today.py — GET/POST /api/v1/today Flask 라우트 테스트.

tests/test_flask_routes.py의 mini_app 패턴(최소 Flask 앱 + db_path monkeypatch)을 따른다.
"""
from __future__ import annotations

import sqlite3

import pytest
from flask import Flask

from src.db_setup import create_tables, migrate_db


@pytest.fixture
def mini_app(tmp_path):
    db_file = tmp_path / "running.db"
    conn = sqlite3.connect(str(db_file))
    create_tables(conn)
    migrate_db(conn)
    conn.close()

    import src.web.helpers as helpers
    _orig = helpers.db_path
    helpers.db_path = lambda: db_file

    import src.api.routes_today as routes_today
    _orig_route = routes_today.db_path
    routes_today.db_path = lambda: db_file

    app = Flask(__name__)
    app.config["TESTING"] = True
    from src.api import api_bp
    app.register_blueprint(api_bp)

    with app.test_client() as client:
        yield client

    helpers.db_path = _orig
    routes_today.db_path = _orig_route


def test_get_today_no_data(mini_app):
    res = mini_app.get("/api/v1/today")
    assert res.status_code == 200
    body = res.get_json()
    assert "data" in body
    assert body["data"]["status"]["date"]
    assert body["data"]["briefing"]["headline"]
    assert body["data"]["recent_activities"] == []


def test_post_checkin_saves_and_returns(mini_app):
    res = mini_app.post("/api/v1/today/checkin", json={"fatigue": 3, "pain": "none", "note": "괜찮음"})
    assert res.status_code == 200
    body = res.get_json()
    assert body["data"]["fatigue"] == 3
    assert body["data"]["note"] == "괜찮음"
    assert body["data"]["saved_at"]


def test_post_checkin_no_body(mini_app):
    res = mini_app.post("/api/v1/today/checkin", json={})
    assert res.status_code == 200
    body = res.get_json()
    assert body["data"]["fatigue"] is None
