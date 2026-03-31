"""auth_cf.py 테스트 — Cloudflare Zero Trust 헤더 기반 사용자 식별."""

import os
import pytest
from flask import Flask, session

import src.web.auth_cf as auth_cf_module


# ── 픽스처 ─────────────────────────────────────────────────────────────────

@pytest.fixture()
def dev_app(monkeypatch) -> Flask:
    """개발 환경 Flask 테스트 앱."""
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DEV_USER_ID", "test_default")
    monkeypatch.setenv("FLASK_SECRET_KEY", "test-secret")
    monkeypatch.setattr(auth_cf_module, "_IS_PRODUCTION", False)

    app = Flask(__name__)
    app.secret_key = "test-secret"
    app.config["TESTING"] = True

    from src.web.auth_cf import init_cf_auth
    init_cf_auth(app)

    @app.get("/ping")
    def ping():
        return {"user_id": session.get("user_id", "none")}

    return app


@pytest.fixture()
def prod_app(monkeypatch) -> Flask:
    """Production 환경 Flask 테스트 앱."""
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setattr(auth_cf_module, "_IS_PRODUCTION", True)

    app = Flask(__name__)
    app.secret_key = "test-secret"
    app.config["TESTING"] = True

    from src.web.auth_cf import init_cf_auth
    init_cf_auth(app)

    @app.get("/ping")
    def ping():
        return {"user_id": session.get("user_id", "none")}

    return app


# ── 개발 환경 ────────────────────────────────────────────────────────────

def test_dev_cf_header_sets_session(dev_app):
    """개발 환경에서 CF 헤더가 있으면 session["user_id"]에 이메일이 세팅된다."""
    with dev_app.test_client() as client:
        resp = client.get("/ping", headers={
            "CF-Access-Authenticated-User-Email": "alice@example.com"
        })
        assert resp.status_code == 200
        assert resp.get_json()["user_id"] == "alice@example.com"


def test_dev_no_header_fallback_to_dev_user(dev_app):
    """개발 환경에서 CF 헤더 없으면 DEV_USER_ID로 fallback된다."""
    with dev_app.test_client() as client:
        resp = client.get("/ping")
        assert resp.status_code == 200
        assert resp.get_json()["user_id"] == "test_default"


def test_dev_session_reused_without_reparse(dev_app):
    """세션에 user_id가 이미 있으면 헤더를 다시 파싱하지 않는다."""
    with dev_app.test_client() as client:
        # 첫 요청: 헤더로 alice 세팅
        client.get("/ping", headers={
            "CF-Access-Authenticated-User-Email": "alice@example.com"
        })
        # 두 번째 요청: 헤더 없어도 세션 유지
        resp = client.get("/ping")
        assert resp.get_json()["user_id"] == "alice@example.com"


def test_dev_email_with_special_chars(dev_app):
    """이메일 주소의 @ . 등 특수문자가 user_id에 그대로 보존된다."""
    with dev_app.test_client() as client:
        resp = client.get("/ping", headers={
            "CF-Access-Authenticated-User-Email": "user.name+tag@my-domain.co.kr"
        })
        assert resp.get_json()["user_id"] == "user.name+tag@my-domain.co.kr"


# ── Production 환경 ──────────────────────────────────────────────────────

def test_prod_cf_header_sets_session(prod_app):
    """Production 환경에서 CF 헤더가 있으면 정상 응답."""
    with prod_app.test_client() as client:
        resp = client.get("/ping", headers={
            "CF-Access-Authenticated-User-Email": "bob@example.com"
        })
        assert resp.status_code == 200
        assert resp.get_json()["user_id"] == "bob@example.com"


def test_prod_no_header_returns_401(prod_app):
    """Production 환경에서 CF 헤더 없으면 401 반환."""
    with prod_app.test_client() as client:
        resp = client.get("/ping")
        assert resp.status_code == 401


def test_prod_empty_header_returns_401(prod_app):
    """Production 환경에서 빈 CF 헤더도 401 반환."""
    with prod_app.test_client() as client:
        resp = client.get("/ping", headers={
            "CF-Access-Authenticated-User-Email": "   "
        })
        assert resp.status_code == 401
