"""POST /data/sources/<p>/connect|test|disconnect — 키 연결·테스트·해제·return_to 검사."""
from __future__ import annotations

import pytest
from flask import Flask

from src.api import api_bp
from src.services import data_connect_service as svc


@pytest.fixture
def env(monkeypatch):
    import src.api.routes_data as rd
    cfg = {"intervals": {"athlete_id": "i1", "api_key": "old"}, "strava": {}, "runalyze": {}}
    writes = []

    def fake_update(name, updates, path=None, *, user_id=None):
        writes.append((name, dict(updates)))
        cfg.setdefault(name, {}).update(updates)
        return cfg

    monkeypatch.setattr(rd, "get_current_user_id", lambda: "u")
    monkeypatch.setattr(rd, "load_config", lambda user_id=None: cfg)
    monkeypatch.setattr(svc, "load_config", lambda user_id=None: cfg)
    monkeypatch.setattr(svc, "update_service_config", fake_update)
    ok = {"v": True}
    monkeypatch.setattr(svc, "_CHECKS", {p: (lambda c: {"ok": ok["v"], "status": "x"}) for p in ("intervals", "runalyze")})
    app = Flask(__name__)
    app.register_blueprint(api_bp)
    with app.test_client() as c:
        yield c, cfg, writes, ok


@pytest.mark.parametrize("v,expected", [
    ("/v2/data/sources/strava?connected=1", True), ("/v2/welcome", True),
    ("//evil.com", False), ("https://evil.com", False), ("/v2/data/../admin", False),
    ("/other", False), (None, False), ("/v2/data/sourcesX", False),
])
def test_safe_return_to(v, expected):
    assert (svc.safe_return_to(v) is not None) is expected


def test_connect_intervals_saves_and_reports(env):
    c, cfg, writes, _ = env
    r = c.post("/api/v1/data/sources/intervals/connect", json={"athlete_id": "i9", "api_key": "SECRETKEY"})
    assert r.status_code == 200 and r.get_json()["data"]["ok"] is True
    assert cfg["intervals"] == {"athlete_id": "i9", "api_key": "SECRETKEY"}
    assert "SECRETKEY" not in r.get_data(as_text=True)


def test_connect_failure_rolls_back(env):
    c, cfg, writes, ok = env
    ok["v"] = False
    r = c.post("/api/v1/data/sources/intervals/connect", json={"athlete_id": "i9", "api_key": "bad"})
    assert r.get_json()["data"]["ok"] is False
    assert cfg["intervals"] == {"athlete_id": "i1", "api_key": "old"}


def test_connect_validation(env):
    c = env[0]
    assert c.post("/api/v1/data/sources/runalyze/connect", json={}).status_code == 400
    assert c.post("/api/v1/data/sources/nope/connect", json={}).status_code == 404
    assert c.post("/api/v1/data/sources/garmin/connect", json={}).status_code == 422
    assert c.post("/api/v1/data/sources/strava/connect", json={}).status_code == 400


def test_connect_strava_redirect_validates_return_to(env):
    c, cfg, *_ = env
    cfg["strava"] = {"client_id": "1", "client_secret": "s"}
    r = c.post("/api/v1/data/sources/strava/connect", json={"return_to": "//evil.com"})
    url = r.get_json()["data"]["redirect_url"]
    assert url.startswith("/connect/strava/oauth-start?") and "evil" not in url
    r = c.post("/api/v1/data/sources/strava/connect", json={"return_to": "/v2/welcome"})
    assert "%2Fv2%2Fwelcome" in r.get_json()["data"]["redirect_url"]


def test_test_endpoint(env):
    c, _, _, ok = env
    assert c.post("/api/v1/data/sources/intervals/test").get_json()["data"]["ok"] is True
    ok["v"] = False
    assert c.post("/api/v1/data/sources/runalyze/test").get_json()["data"]["ok"] is False


def test_disconnect_clears_credentials_only_keep_data(env):
    c, cfg, writes, _ = env
    assert c.post("/api/v1/data/sources/intervals/disconnect", json={"keep_data": False}).status_code == 400
    r = c.post("/api/v1/data/sources/intervals/disconnect", json={"keep_data": True})
    assert r.status_code == 200 and cfg["intervals"] == {"athlete_id": "", "api_key": ""}
