"""사용자 설정 서비스·API 테스트."""
import sqlite3

import pytest
from flask import Flask

from src.db_setup import create_tables
from src.services import user_settings_service as svc


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    return c


def test_whitelist_and_invalid_value(conn):
    with pytest.raises(ValueError):
        svc.set_setting(conn, "other", "v2")
    with pytest.raises(ValueError):
        svc.set_setting(conn, "ui_default", "v3")


def test_resolve_priority(conn):
    assert svc.resolve_ui_default(conn, {}) == "v1"
    assert svc.resolve_ui_default(conn, {"ui_default_global": "v2"}) == "v2"
    svc.set_setting(conn, "ui_default", "v1")
    assert svc.resolve_ui_default(conn, {"ui_default_global": "v2"}) == "v1"


def test_set_overwrites(conn):
    svc.set_setting(conn, "ui_default", "v2")
    svc.set_setting(conn, "ui_default", "v1")
    assert svc.get_setting(conn, "ui_default") == "v1"


def test_invalid_global_falls_back(conn):
    assert svc.resolve_ui_default(conn, {"ui_default_global": "zzz"}) == "v1"


@pytest.fixture
def client(tmp_path, monkeypatch):
    f = tmp_path / "running.db"
    c = sqlite3.connect(str(f))
    create_tables(c)
    c.close()
    import src.api.routes_me as r
    monkeypatch.setattr(r, "db_path", lambda: f)
    monkeypatch.setattr(r, "load_config", lambda: {"ui_default_global": "v1"})
    app = Flask(__name__)
    from src.api import api_bp
    app.register_blueprint(api_bp)
    with app.test_client() as cl:
        yield cl


def test_api_get_patch(client):
    assert client.get("/api/v1/me/preferences").get_json()["data"] == {
        "ui_default": "v1", "ui_default_global": "v1", "onboarding": "pending", "onboarding_step": 0}
    r = client.patch("/api/v1/me/preferences", json={"ui_default": "v2"})
    assert r.get_json()["data"]["ui_default"] == "v2"


def test_api_patch_invalid_400(client):
    assert client.patch("/api/v1/me/preferences", json={"ui_default": "x"}).status_code == 400
    assert client.patch("/api/v1/me/preferences", json={}).status_code == 400


def test_api_state_persists(client):
    client.patch("/api/v1/me/preferences", json={"ui_default": "v2"})
    assert client.get("/api/v1/me/preferences").get_json()["data"]["ui_default"] == "v2"


def test_api_onboarding_patch(client):
    r = client.patch("/api/v1/me/preferences", json={"onboarding": "skipped", "onboarding_step": 2})
    d = r.get_json()["data"]
    assert (d["onboarding"], d["onboarding_step"]) == ("skipped", 2)
    assert client.patch("/api/v1/me/preferences", json={"onboarding_step": 9}).status_code == 400


def test_entry_path(conn):
    assert svc.entry_path(conn, {}) == "/dashboard"
    assert svc.entry_path(None, {"ui_default_global": "v2"}) == "/v2/today"
    svc.set_setting(conn, "ui_default", "v2")
    assert svc.entry_path(conn, {}) == "/v2/today"
    svc.set_setting(conn, "ui_default", "v1")
    assert svc.entry_path(conn, {"ui_default_global": "v2"}) == "/dashboard"
