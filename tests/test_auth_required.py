"""E-03 — 401 응답: 화면 요청은 로그인 안내 HTML, /api/ 는 JSON 봉투."""
import pytest
from flask import Flask

import src.web.auth_cf as auth_cf_module
from src.web.auth_required import auth_required_response, login_target


def test_login_target_registry_uses_safe_next():
    assert login_target("/v2/library", "", True) == ("/auth/start?next=/v2/library", "다시 로그인")
    assert login_target("//evil.com", "", True)[0] == "/auth/start?next=/v2/today"


def test_login_target_legacy_reopens_same_path():
    assert login_target("/v2/today", "a=1", False) == ("/v2/today?a=1", "다시 시도")
    assert login_target("//evil.com", "", False)[0] == "/"


def test_auth_required_response_escapes_message():
    app = Flask(__name__)
    with app.test_request_context("/v2/x"):
        resp = auth_required_response("AUTH_REQUIRED", "<b>x</b>", registry_mode=False)
    body = resp.get_data(as_text=True)
    assert resp.status_code == 401 and resp.mimetype == "text/html"
    assert "&lt;b&gt;" in body and "<b>x" not in body
    assert resp.headers["Cache-Control"] == "no-store"


@pytest.fixture()
def prod_app(monkeypatch) -> Flask:
    monkeypatch.delenv("AUTH_MODE", raising=False)
    monkeypatch.setattr(auth_cf_module, "_IS_PRODUCTION", True)
    app = Flask(__name__)
    app.secret_key = "t"
    auth_cf_module.init_cf_auth(app)

    @app.get("/v2/today")
    def today():
        return "ok"

    @app.get("/api/v1/today")
    def api_today():
        return {"ok": True}

    return app


def test_prod_page_without_header_shows_login_html(prod_app):
    resp = prod_app.test_client().get("/v2/today")
    assert resp.status_code == 401 and resp.mimetype == "text/html"
    text = resp.get_data(as_text=True)
    assert "로그인이 필요해요" in text and 'href="/v2/today"' in text


def test_prod_api_without_header_is_json_envelope(prod_app):
    resp = prod_app.test_client().get("/api/v1/today")
    assert resp.status_code == 401
    assert resp.get_json()["error"]["code"] == "AUTH_REQUIRED"
