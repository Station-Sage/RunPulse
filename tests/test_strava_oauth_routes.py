"""views_strava_oauth — v1 화면 없이 결과를 return_to 또는 v2 Strava 화면으로 돌려보내는지 (S4-91)."""
from __future__ import annotations

import urllib.parse

import pytest
from flask import Flask

import src.web.views_strava_oauth as so

V2 = so.V2_STRAVA_PATH


@pytest.fixture
def client(monkeypatch):
    cfg = {"strava": {"client_id": "cid", "client_secret": "sec"}}
    saved: dict = {}
    monkeypatch.setattr(so, "load_config", lambda *a, **k: cfg)
    monkeypatch.setattr(so, "update_service_config", lambda svc, upd, **k: saved.update({svc: upd}))
    app = Flask(__name__)
    app.register_blueprint(so.strava_oauth_bp)
    with app.test_client() as c:
        c.cfg, c.saved = cfg, saved
        yield c


def test_oauth_start_redirects_to_strava_with_state(client):
    r = client.get("/connect/strava/oauth-start?return_to=/v2/welcome?step=2")
    assert r.status_code == 302 and r.headers["Location"].startswith(so._STRAVA_AUTH_URL)
    qs = urllib.parse.parse_qs(urllib.parse.urlparse(r.headers["Location"]).query)
    assert qs["client_id"] == ["cid"] and qs["state"] == ["/v2/welcome?step=2"]
    assert qs["redirect_uri"][0].endswith("/connect/strava/callback")


def test_oauth_start_without_client_id_goes_to_v2(client):
    client.cfg["strava"] = {}
    r = client.get("/connect/strava/oauth-start")
    assert r.headers["Location"] == f"{V2}?connect_error=1"


def test_callback_error_with_state_returns_to_caller(client):
    r = client.get("/connect/strava/callback?error=access_denied&state=/v2/welcome?step=2")
    assert r.headers["Location"] == "/v2/welcome?connect_error=1"


def test_callback_without_code_goes_to_v2(client):
    assert client.get("/connect/strava/callback").headers["Location"] == f"{V2}?connect_error=1"


def test_callback_success_saves_tokens(client, monkeypatch):
    class _Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"access_token": "a", "refresh_token": "r", "expires_at": 9}

    class _Client:
        def __init__(self, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def post(self, url, data):
            assert data["code"] == "c1"
            return _Resp()

    import httpx
    monkeypatch.setattr(httpx, "Client", _Client)
    r = client.get("/connect/strava/callback?code=c1")
    assert r.headers["Location"] == f"{V2}?connected=1"
    assert client.saved["strava"]["refresh_token"] == "r"


def test_fail_helper_strips_query():
    app = Flask(__name__)
    with app.test_request_context("/"):
        assert so._fail("/v2/x?a=1", "t").headers["Location"] == "/v2/x?connect_error=1"
        assert so._fail(None, "t").headers["Location"] == f"{V2}?connect_error=1"
