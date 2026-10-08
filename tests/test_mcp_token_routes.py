"""웹 토큰 발급 API — 세션 사용자 한정, 원문 1회 노출, 상한·폐기·감사."""
from __future__ import annotations

import sqlite3

import pytest
from flask import Flask

from src.api import api_bp
from src.api import routes_mcp_tokens as r
from src.db_setup import create_tables
from src.mcp_remote import audit
from src.mcp_remote import token_index as ti
from src.web import views_mcp_remote as v

URL = "/api/v1/settings/mcp-tokens"


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(ti, "index_path", lambda: tmp_path / "mcp_tokens.db")
    users = tmp_path / "users"
    monkeypatch.setattr(ti, "get_db_path", lambda uid=None, create=True: users / (uid or "default") / "running.db")
    for u in ("u1", "u2"):
        (users / u).mkdir(parents=True)
        c = sqlite3.connect(users / u / "running.db")
        create_tables(c)
        c.commit()
        c.close()
    monkeypatch.setattr(audit, "_last_purge_day", "9999")
    monkeypatch.setattr(v, "enabled", lambda: False)
    state = {"uid": "u1"}
    monkeypatch.setattr(r, "get_current_user_id", lambda: state["uid"])
    app = Flask(__name__)
    app.register_blueprint(api_bp)
    c = app.test_client()
    c.state = state
    return c


def test_issue_shows_plaintext_once_and_list_hides_it(client):
    res = client.post(URL, json={"label": "Genspark"})
    assert res.status_code == 201 and res.headers["Cache-Control"] == "no-store"
    data = res.get_json()["data"]
    assert data["token"].startswith("rpmcp_")
    lst = client.get(URL).get_json()["data"]
    assert lst["enabled"] is False and lst["max_active"] == 5
    assert len(lst["tokens"]) == 1 and "token" not in lst["tokens"][0]
    assert data["token"] not in client.get(URL).get_data(as_text=True)


def test_label_required_and_bad_days(client):
    assert client.post(URL, json={"label": "  "}).status_code == 400
    assert client.post(URL, json={"label": "x", "days": "abc"}).status_code == 400
    assert client.post(URL, json={"label": "x", "days": 9999}).status_code == 409


def test_cap_returns_409(client):
    for i in range(5):
        assert client.post(URL, json={"label": f"t{i}"}).status_code == 201
    assert client.post(URL, json={"label": "6"}).status_code == 409


def test_revoke_is_user_scoped_and_audited(client):
    tid = client.post(URL, json={"label": "a"}).get_json()["data"]["token_id"]
    client.state["uid"] = "u2"
    assert client.delete(f"{URL}/{tid}").status_code == 404
    assert client.get(URL).get_json()["data"]["tokens"] == []
    client.state["uid"] = "u1"
    assert client.delete(f"{URL}/{tid}").status_code == 204
    assert client.get(URL).get_json()["data"]["tokens"] == []
    methods = [x["method"] for x in audit.query("u1", None, 10)]
    assert "token_issue" in methods and "token_revoke" in methods
