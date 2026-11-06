"""`/api/v1/data/sources/garmin/*`(T5·T8) — 상태코드·레이트리밋·쿨다운·no-store·비밀 미노출·로컬 키트."""
from __future__ import annotations

import pytest
from flask import Flask

from src.api import api_bp
from src.services import garmin_connect_service as svc
from src.services import garmin_mfa_store as store
from src.utils import rate_window
from src.utils.config import update_service_config
from tests.helpers_garmin import AUTH, TOO_MANY, install

UID = "u1@x.com"
PW = "s3cret-PW!"
H = {"Origin": "http://localhost"}
BASE = "/api/v1/data/sources/garmin"


@pytest.fixture
def client(isolated_users_root, monkeypatch):
    import src.api.routes_data as rd
    import src.api.routes_data_garmin as rg

    rate_window.reset()
    store.reset()
    store.set_multi_worker(False)
    user = {"id": UID}
    monkeypatch.setattr(rg, "get_current_user_id", lambda: user["id"])
    monkeypatch.setattr(rd, "get_current_user_id", lambda: user["id"])
    app = Flask(__name__)
    app.register_blueprint(api_bp)
    with app.test_client() as c:
        c.user = user
        yield c
    rate_window.reset()
    store.reset()


def _post(c, path, body, ip="1.1.1.1"):
    return c.post(BASE + path, json=body, headers={**H, "CF-Connecting-IP": ip})


def test_connect_success_no_store_and_no_secrets(client, monkeypatch):
    install(monkeypatch, svc)
    r = _post(client, "/connect", {"email": "a@x.com", "password": PW})
    assert r.status_code == 200 and r.get_json()["data"]["status"] == "connected"
    assert r.headers["Cache-Control"] == "no-store"
    text = r.get_data(as_text=True)
    assert PW not in text and "NEW" not in text and "tokenstore" not in text


def test_connect_validation_400(client, monkeypatch):
    install(monkeypatch, svc)
    r = _post(client, "/connect", {"email": "", "password": PW})
    assert r.status_code == 400 and r.get_json()["error"]["code"] == "INVALID_PARAM"


def test_connect_auth_failed_401_with_code(client, monkeypatch):
    install(monkeypatch, svc, {"login": AUTH("raw upstream text")})
    r = _post(client, "/connect", {"email": "a@x.com", "password": PW})
    assert r.status_code == 401 and r.get_json()["error"]["code"] == "GARMIN_AUTH_FAILED"
    assert "raw upstream" not in r.get_data(as_text=True)


def test_upstream_429_cooldown_retry_after_and_no_calls(client, monkeypatch):
    _, calls = install(monkeypatch, svc, {"login": TOO_MANY("x")})
    r = _post(client, "/connect", {"email": "a@x.com", "password": PW})
    assert r.status_code == 503 and r.headers["Retry-After"] == "900"
    assert r.get_json()["error"]["code"] == "GARMIN_RATE_LIMITED"
    n = len(calls)
    r = _post(client, "/connect", {"email": "a@x.com", "password": PW})
    assert r.status_code == 503 and len(calls) == n


def test_local_rate_limit_uid_5_per_15m(client, monkeypatch):
    _, calls = install(monkeypatch, svc, {"login": AUTH("x")})
    codes = [_post(client, "/connect", {"email": "a@x.com", "password": PW}).status_code for _ in range(6)]
    assert codes == [401] * 5 + [429]
    assert sum(1 for c in calls if c[0] == "login") == 5


def test_local_rate_limit_ip_10(client, monkeypatch):
    install(monkeypatch, svc, {"login": AUTH("x")})
    codes = []
    for i in range(11):
        client.user["id"] = f"u{i}@x.com"
        codes.append(_post(client, "/connect", {"email": "a@x.com", "password": PW}, ip="9.9.9.9").status_code)
    assert codes[:10] == [401] * 10 and codes[10] == 429


def test_mfa_flow_and_cross_user(client, monkeypatch):
    install(monkeypatch, svc, {"login": ("needs_mfa", None), "resume": [AUTH("bad")]})
    d = _post(client, "/connect", {"email": "a@x.com", "password": PW}).get_json()["data"]
    assert d["status"] == "needs_mfa" and d["expires_in"] == 300 and PW not in str(d)
    r = _post(client, "/mfa", {"mfa_ticket": d["mfa_ticket"], "code": "111111"})
    assert r.status_code == 422 and r.get_json()["error"]["details"] == {"attempts_left": 4}
    client.user["id"] = "u2@x.com"
    r = _post(client, "/mfa", {"mfa_ticket": d["mfa_ticket"], "code": "123456"})
    assert r.status_code == 410 and r.get_json()["error"]["code"] == "MFA_EXPIRED"
    client.user["id"] = UID
    r = _post(client, "/mfa", {"mfa_ticket": d["mfa_ticket"], "code": "123456"})
    assert r.status_code == 200 and r.get_json()["data"]["status"] == "connected"
    assert r.headers["Cache-Control"] == "no-store"
    assert _post(client, "/mfa", {"mfa_ticket": d["mfa_ticket"], "code": "123456"}).status_code == 410


def test_mfa_bad_code_400_and_rate_limit(client):
    assert _post(client, "/mfa", {"mfa_ticket": "t", "code": "12"}).status_code == 400
    codes = [_post(client, "/mfa", {"mfa_ticket": "t", "code": "123456"}).status_code for _ in range(10)]
    assert codes[-1] == 429 and set(codes[:-1]) == {410}


def test_mfa_cancel_idempotent(client, monkeypatch):
    install(monkeypatch, svc, {"login": ("needs_mfa", None)})
    t = _post(client, "/connect", {"email": "a@x.com", "password": PW}).get_json()["data"]["mfa_ticket"]
    for _ in range(2):
        r = _post(client, "/mfa/cancel", {})
        assert r.status_code == 200 and r.get_json()["data"] == {"status": "disconnected"}
    assert _post(client, "/mfa", {"mfa_ticket": t, "code": "123456"}).status_code == 410


def test_mfa_unavailable_503(client):
    store.set_multi_worker(True)
    r = _post(client, "/mfa", {"mfa_ticket": "t", "code": "123456"})
    assert r.status_code == 503 and r.get_json()["error"]["code"] == "MFA_UNAVAILABLE"
    store.set_multi_worker(False)


def test_token_paste(client, monkeypatch):
    install(monkeypatch, svc)
    assert _post(client, "/token", {"token_json": "{}"}).status_code == 400
    r = _post(client, "/token", {"token_json": '{"di_token": "SECRET_TOK"}'})
    assert r.status_code == 200 and "SECRET_TOK" not in r.get_data(as_text=True)
    assert r.headers["Cache-Control"] == "no-store"
    install(monkeypatch, svc, {"login": AUTH("x")})
    assert _post(client, "/token", {"token_json": '{"di_token": "a"}'}).status_code == 401


def test_generic_disconnect_and_test_still_work(client, monkeypatch):
    install(monkeypatch, svc)
    _post(client, "/connect", {"email": "a@x.com", "password": PW})
    r = client.post(BASE + "/disconnect", json={"keep_data": True}, headers=H)
    assert r.status_code == 200 and not (svc.token_dir(UID) / "garmin_tokens.json").exists()


def test_local_kit_env_blanks_cf_secret(client, monkeypatch):
    import src.api.routes_data_garmin as rg

    update_service_config("garmin", {"email": "a@x.com"}, user_id=UID)
    real = rg.load_config
    monkeypatch.setattr(rg, "load_config", lambda user_id=None: (
        {"cf": {"service_client_id": "cid.access", "service_client_secret": "TOPSECRET"}} if user_id == "default" else real(user_id=user_id)))
    r = client.get(BASE + "/local-kit/env")
    text = r.get_data(as_text=True)
    assert r.status_code == 200 and "attachment" in r.headers["Content-Disposition"]
    assert "TOPSECRET" not in text and "CF_SERVICE_CLIENT_ID=cid.access" in text
    assert f"RUNPULSE_USER_ID={UID}" in text and "GARMIN_EMAIL=a@x.com" in text
    assert r.headers["Cache-Control"] == "no-store"


def test_local_kit_script(client):
    r = client.get(BASE + "/local-kit/script")
    assert r.status_code == 200 and b"garmin" in r.data.lower()
    assert "garmin_local_sync.py" in r.headers["Content-Disposition"]
    r.close()
