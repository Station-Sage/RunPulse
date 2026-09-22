"""tests/test_api_coach.py — /api/v1/coach/threads(+:id, +:id/messages) 테스트.

chat_engine.chat()은 monkeypatch로 결정적 응답 대체 — test_coach_service.py의
_fake_ai_chat 패턴 재사용, AI provider 체인 의존성 제거가 목적.
"""
from __future__ import annotations

import sqlite3

import pytest
from flask import Flask

from src.db_setup import create_tables, migrate_db


@pytest.fixture(autouse=True)
def _fake_ai_chat(monkeypatch):
    def _fake(conn, user_message, config=None, chip_id=None, thread_id=None):
        return f"[fake] {user_message}에 대한 응답", "fake"

    monkeypatch.setattr("src.ai.chat_engine.chat", _fake)


@pytest.fixture
def mini_app(tmp_path):
    db_file = tmp_path / "running.db"
    conn = sqlite3.connect(str(db_file))
    create_tables(conn)
    migrate_db(conn)
    conn.close()

    import src.api.routes_coach as routes_coach
    _orig_route = routes_coach.db_path
    routes_coach.db_path = lambda: db_file

    app = Flask(__name__)
    app.config["TESTING"] = True
    from src.api import api_bp
    app.register_blueprint(api_bp)

    with app.test_client() as client:
        yield client

    routes_coach.db_path = _orig_route


def test_list_threads_empty(mini_app):
    res = mini_app.get("/api/v1/coach/threads")
    assert res.status_code == 200
    assert mini_app.get("/api/v1/coach/threads").get_json()["data"]["threads"] == []


def test_create_thread(mini_app):
    res = mini_app.post("/api/v1/coach/threads", json={"initial_message": "오늘 뭐 할까?"})
    assert res.status_code == 201
    body = res.get_json()
    assert body["data"]["thread"]["id"]
    assert body["data"]["message"]["role"] == "assistant"


def test_create_thread_missing_message(mini_app):
    res = mini_app.post("/api/v1/coach/threads", json={})
    assert res.status_code == 400
    assert res.get_json()["error"]["code"] == "INVALID_PARAM"


def test_get_thread_detail(mini_app):
    created = mini_app.post("/api/v1/coach/threads", json={"initial_message": "첫 질문"}).get_json()
    thread_id = created["data"]["thread"]["id"]

    res = mini_app.get(f"/api/v1/coach/threads/{thread_id}")
    assert res.status_code == 200
    body = res.get_json()
    assert body["data"]["thread"]["id"] == thread_id
    assert len(body["data"]["messages"]) == 2


def test_get_thread_detail_not_found(mini_app):
    res = mini_app.get("/api/v1/coach/threads/9999")
    assert res.status_code == 404


def test_add_message(mini_app):
    created = mini_app.post("/api/v1/coach/threads", json={"initial_message": "첫 질문"}).get_json()
    thread_id = created["data"]["thread"]["id"]

    res = mini_app.post(f"/api/v1/coach/threads/{thread_id}/messages", json={"content": "추가 질문"})
    assert res.status_code == 201
    body = res.get_json()
    assert body["data"]["message"]["role"] == "assistant"
    assert body["data"]["message"]["thread_id"] == thread_id


def test_add_message_thread_not_found(mini_app):
    res = mini_app.post("/api/v1/coach/threads/9999/messages", json={"content": "질문"})
    assert res.status_code == 404


def test_add_message_missing_content(mini_app):
    created = mini_app.post("/api/v1/coach/threads", json={"initial_message": "첫 질문"}).get_json()
    thread_id = created["data"]["thread"]["id"]

    res = mini_app.post(f"/api/v1/coach/threads/{thread_id}/messages", json={})
    assert res.status_code == 400
