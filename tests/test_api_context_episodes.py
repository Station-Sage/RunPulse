"""/api/context-episodes* — 목록·생성·확정·종료·삭제·동의 + 봉투 오류."""
import sqlite3

import pytest
from flask import Flask

from src.db_setup import create_tables, migrate_db

H = {"Origin": "http://localhost"}


@pytest.fixture
def client(tmp_path, monkeypatch):
    f = tmp_path / "running.db"
    c = sqlite3.connect(str(f))
    create_tables(c)
    migrate_db(c)
    c.commit()
    c.close()
    import src.api.routes_context as m
    monkeypatch.setattr(m, "db_path", lambda: f)
    app = Flask(__name__)
    app.register_blueprint(m.context_bp)
    return app.test_client()


def test_create_list_close_illness(client):
    r = client.post("/api/context-episodes", json={"kind": "illness", "severity": 2, "detail": {"site": "목"}}, headers=H)
    assert r.status_code == 201
    d = r.get_json()["data"]
    assert d["needs_consent_prompt"] is True and d["episode"]["status"] == "confirmed"
    eid = d["episode"]["id"]
    lst = client.get("/api/context-episodes").get_json()["data"]
    assert [e["id"] for e in lst["episodes"]] == [eid] and lst["consent"]["needs_first_prompt"] is True
    r = client.post(f"/api/context-episodes/{eid}/close", json={}, headers=H)
    assert r.status_code == 200 and r.get_json()["data"]["episode"]["end_date"]
    assert client.post(f"/api/context-episodes/{eid}/close", json={}, headers=H).status_code == 409


def test_validation_errors_are_envelopes(client):
    r = client.post("/api/context-episodes", json={"kind": "flu"}, headers=H)
    assert r.status_code == 400 and r.get_json()["error"]["code"] == "INVALID_PARAM"
    r = client.post("/api/context-episodes", json={"kind": "illness", "severity": 9}, headers=H)
    assert r.status_code == 400
    r = client.post("/api/context-episodes", data="x", headers=H)
    assert r.status_code == 415


def test_dismiss_only_candidates_and_confirm(client):
    eid = client.post("/api/context-episodes", json={"kind": "travel", "detail": {"delta_h": 5}}, headers=H) \
        .get_json()["data"]["episode"]["id"]
    assert client.post(f"/api/context-episodes/{eid}/dismiss", headers=H).status_code == 409
    assert client.post(f"/api/context-episodes/{eid}/confirm", headers=H).status_code == 200
    assert client.post("/api/context-episodes/999/confirm", headers=H).status_code == 409


def test_delete_with_chat_threads_and_404(client):
    eid = client.post("/api/context-episodes", json={"kind": "altitude", "detail": {"altitude_m": 2000}}, headers=H) \
        .get_json()["data"]["episode"]["id"]
    r = client.delete(f"/api/context-episodes/{eid}", json={"chat_thread_ids": [1, 1, 2]}, headers=H)
    assert r.status_code == 200 and r.get_json()["data"]["kind"] == "altitude"
    assert client.delete(f"/api/context-episodes/{eid}", headers=H).status_code == 404
    assert client.delete("/api/context-episodes/1", json={"chat_thread_ids": ["a"]}, headers=H).status_code == 400


def test_consent_roundtrip(client):
    assert client.get("/api/context-episodes/consent").get_json()["data"]["needs_first_prompt"] is True
    r = client.post("/api/context-episodes/consent", json={"action": "grant", "via": "first_input"}, headers=H)
    assert r.status_code == 201 and r.get_json()["data"]["action"] == "grant"
    d = client.get("/api/context-episodes/consent").get_json()["data"]
    assert d == {"action": "grant", "needs_first_prompt": False}
    assert client.post("/api/context-episodes/consent", json={"action": "x", "via": "settings"}, headers=H).status_code == 400


def test_today_context_block_and_forged_origin(tmp_path, monkeypatch):
    from src.services import context_today
    from tests.helpers_pred import mem_conn
    c = mem_conn()
    ctx = context_today.build(c)
    assert ctx == {"active": [], "illness_reconfirm": None, "health_question": False}
    from src.services import context_episodes as eps
    eps.open_episode(c, "travel", detail={"delta_h": 5})
    assert len(context_today.build(c)["active"]) == 1
