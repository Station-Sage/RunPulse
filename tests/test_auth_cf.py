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


# ── V1-20: uid 규칙 위반 → 403 + 마스킹 보안 로그 (S3 3단계) ─────────────────

import logging  # noqa: E402

_EVIL = ["../etc/passwd@evil.com", "a/b@x.com", ".hidden@x.com", "a b@x.com", "x" * 300]


@pytest.mark.parametrize("email", _EVIL)
def test_invalid_cf_email_403_no_session_masked_log(dev_app, caplog, email):
    with dev_app.test_client() as client, caplog.at_level(logging.WARNING, logger="runpulse.security"):
        resp = client.get("/ping", headers={"CF-Access-Authenticated-User-Email": email})
        assert resp.status_code == 403
        assert resp.mimetype == "text/plain"  # 봉투 경로가 아니므로 일반 403
        with client.session_transaction() as sess:
            assert "user_id" not in sess  # 세션에 기록하지 않았다 — default 로 폴백도 없다
    text = " ".join(r.getMessage() for r in caplog.records)
    assert "cf_email" in text
    assert email not in text and "passwd" not in text  # 원문 미기록


def test_invalid_cf_email_in_prod_is_403_not_401(prod_app):
    with prod_app.test_client() as client:
        resp = client.get("/ping", headers={"CF-Access-Authenticated-User-Email": "../x@evil.com"})
        assert resp.status_code == 403


def test_invalid_cf_email_on_envelope_path_is_json_403(dev_app):
    @dev_app.get("/api/v1/zz")
    def zz():
        return {"ok": 1}

    with dev_app.test_client() as client:
        resp = client.get("/api/v1/zz", headers={"CF-Access-Authenticated-User-Email": "a/b@x.com"})
        assert resp.status_code == 403
        assert resp.get_json()["error"]["code"] == "FORBIDDEN_USER"


def test_session_with_invalid_stored_uid_is_403_and_key_cleared(dev_app, caplog):
    """규칙 도입 전에 만들어진 세션의 위반 값 — 조기 통과 전에 검증하고 키를 지운다."""
    with dev_app.test_client() as client, caplog.at_level(logging.WARNING, logger="runpulse.security"):
        with client.session_transaction() as sess:
            sess["user_id"] = "../../victim"
        resp = client.get("/ping")
        assert resp.status_code == 403
        with client.session_transaction() as sess:
            assert "user_id" not in sess
        # 다음 요청은 CF 헤더로 다시 식별된다
        resp = client.get("/ping", headers={"CF-Access-Authenticated-User-Email": "ok@example.com"})
        assert resp.status_code == 200 and resp.get_json()["user_id"] == "ok@example.com"
    text = " ".join(r.getMessage() for r in caplog.records)
    assert "source=session" in text and "victim" not in text


def test_session_with_valid_uid_still_passes(dev_app):
    with dev_app.test_client() as client:
        with client.session_transaction() as sess:
            sess["user_id"] = "alice@example.com"
        assert client.get("/ping").get_json()["user_id"] == "alice@example.com"


def test_invalid_dev_user_id_is_403_no_default_fallback(dev_app, monkeypatch):
    monkeypatch.setenv("DEV_USER_ID", "../boom")
    with dev_app.test_client() as client:
        resp = client.get("/ping")
        assert resp.status_code == 403
        with client.session_transaction() as sess:
            assert "user_id" not in sess


def test_invalid_svc_user_is_403(prod_app, monkeypatch, caplog):
    monkeypatch.setattr(auth_cf_module, "_load_svc_token", lambda: ("cid", "csecret", "../svc"))
    with prod_app.test_client() as client, caplog.at_level(logging.WARNING, logger="runpulse.security"):
        resp = client.get("/ping", headers={"CF-Access-Client-Id": "cid", "CF-Access-Client-Secret": "csecret"})
        assert resp.status_code == 403
        with client.session_transaction() as sess:
            assert "user_id" not in sess
    assert "svc_user" in " ".join(r.getMessage() for r in caplog.records)


def test_valid_svc_user_still_passes(prod_app, monkeypatch):
    monkeypatch.setattr(auth_cf_module, "_load_svc_token", lambda: ("cid", "csecret", "svc@example.com"))
    with prod_app.test_client() as client:
        resp = client.get("/ping", headers={"CF-Access-Client-Id": "cid", "CF-Access-Client-Secret": "csecret"})
        assert resp.status_code == 200 and resp.get_json()["user_id"] == "svc@example.com"


def test_get_db_path_value_error_does_not_become_html_500(dev_app):
    """이중 방어: 규칙 통과 후 깊은 곳(get_db_path)에서 InvalidUserId 가 올라와도 403 으로 처리된다."""
    from src.utils.user_context import InvalidUserId

    @dev_app.errorhandler(InvalidUserId)
    def _h(exc):
        from src.web.request_guard import forbidden_response
        return forbidden_response("FORBIDDEN_USER", "x")

    @dev_app.get("/deep")
    def deep():
        from src.db_setup import get_db_path
        get_db_path("..", create=False)

    with dev_app.test_client() as client:
        assert client.get("/deep").status_code == 403


def test_app_level_handler_registered_in_create_app(tmp_path, monkeypatch):
    """실제 앱 조립(create_app)에 InvalidUserId 핸들러가 있고, 봉투 경로에서는 JSON 403 이 나간다."""
    from src.utils.user_context import InvalidUserId
    from src.web.app import create_app

    monkeypatch.setenv("FLASK_SECRET_KEY", "k")
    import src.db_setup as dbs
    monkeypatch.setattr(dbs, "_PROJECT_ROOT", tmp_path)  # 실제 data/users 에 빈 DB 가 생기지 않게 격리
    app = create_app()
    assert InvalidUserId in app.error_handler_spec[None][None]
    import src.api.routes_today as rt
    monkeypatch.setattr(rt, "db_path", lambda: (_ for _ in ()).throw(InvalidUserId("..***(len=2)")))
    app.config["TESTING"] = True
    with app.test_client() as client:
        resp = client.get("/api/v1/today", headers={"CF-Access-Authenticated-User-Email": "ok@example.com"})
    assert resp.status_code == 403
    assert resp.get_json()["error"]["code"] == "FORBIDDEN_USER"
