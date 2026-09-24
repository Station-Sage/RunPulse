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
    assert body["data"]["checkin"] is None


def test_get_today_reflects_saved_checkin(mini_app):
    mini_app.post("/api/v1/today/checkin", json={"fatigue": 6, "pain": "none"})
    res = mini_app.get("/api/v1/today")
    body = res.get_json()
    assert body["data"]["checkin"]["fatigue"] == 6


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


def test_get_today_checkin_none(mini_app):
    res = mini_app.get("/api/v1/today/checkin")
    assert res.status_code == 200
    body = res.get_json()
    assert body["data"]["checkin"] is None


def test_get_today_checkin_after_post(mini_app):
    mini_app.post("/api/v1/today/checkin", json={"fatigue": 6, "pain": "none"})
    res = mini_app.get("/api/v1/today/checkin")
    assert res.status_code == 200
    body = res.get_json()
    assert body["data"]["checkin"]["fatigue"] == 6


def test_get_today_narrative_no_data(mini_app):
    res = mini_app.get("/api/v1/today/narrative")
    assert res.status_code == 200
    body = res.get_json()
    data = body["data"]
    assert data["source"] == "rule"
    assert isinstance(data["text"], str)
    assert len(data["text"]) > 0
    assert isinstance(data["evidence"], list)
    assert isinstance(data["milestones"], list)


def test_get_today_narrative_highlights_field(mini_app):
    """highlights 필드가 항상 응답에 포함된다."""
    res = mini_app.get("/api/v1/today/narrative")
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert "highlights" in data
    h = data["highlights"]
    assert "total_distance_km" in h
    assert "activity_count" in h
    assert "longest_run_km" in h
    assert "peak_ctl" in h


def test_get_today_narrative_year_month_params(mini_app):
    """?year=&month= 쿼리 파라미터가 정상 수락되고 200 반환."""
    res = mini_app.get("/api/v1/today/narrative?year=2026&month=8")
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert isinstance(data["text"], str)
    assert "highlights" in data


def test_get_today_narrative_invalid_year_month(mini_app):
    """잘못된 year/month → 무시하고 기본 동작(오늘 기준) 반환."""
    res = mini_app.get("/api/v1/today/narrative?year=abc&month=xyz")
    assert res.status_code == 200
    assert res.get_json()["data"]["source"] == "rule"


def test_get_race_hub_no_goal(mini_app):
    """빈 DB → 200, data.goal is None."""
    res = mini_app.get("/api/v1/today/race-hub")
    assert res.status_code == 200
    body = res.get_json()
    assert "data" in body
    assert body["data"]["goal"] is None


def test_get_library_archive_empty(mini_app, monkeypatch):
    import src.api.routes_library as routes_library
    import src.web.helpers as helpers
    monkeypatch.setattr(routes_library, "db_path", helpers.db_path)  # mini_app이 패치한 경로
    res = mini_app.get("/api/v1/library/archive")
    assert res.status_code == 200
    assert res.get_json()["data"]["totals"] is None
