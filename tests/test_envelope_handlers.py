"""tests/test_envelope_handlers.py — register_envelope_handlers (SRV 2.3, ADR-048 1단계).

블루프린트 안에서 난 HTTP 오류·미처리 예외가 `{error:{code,message}}` 봉투로 나가는지 확인한다.
Flask 제약: 어떤 라우트에도 매칭되지 않은 URL 의 404 는 블루프린트 핸들러 밖이라 이 테스트 대상이 아니다.
"""
from __future__ import annotations

import logging

import pytest
from flask import Blueprint, Flask, abort, request

from src.api import api_bp, register_envelope_handlers


@pytest.fixture
def client():
    bp = Blueprint("envtest", __name__, url_prefix="/envtest")

    @bp.get("/boom")
    def boom():
        raise AttributeError("secret internal detail")

    @bp.get("/missing")
    def missing():
        abort(404)

    @bp.get("/bad")
    def bad():
        abort(400, description="잘못된 요청")

    @bp.get("/not-allowed")
    def not_allowed():
        abort(405)

    @bp.post("/only-post")
    def only_post():
        return {"ok": True}

    @bp.post("/body")
    def body():
        request.get_data()
        return {"ok": True}

    @bp.get("/teapot")
    def teapot():
        abort(418)

    register_envelope_handlers(bp)

    app = Flask(__name__)
    app.config["TESTING"] = True  # 예외 전파 모드에서도 핸들러가 우선해야 한다
    app.config["MAX_CONTENT_LENGTH"] = 16
    app.register_blueprint(bp)
    with app.test_client() as c:
        yield c


def _err(res):
    body = res.get_json()
    assert set(body) == {"error"}
    assert set(body["error"]) >= {"code", "message"}
    assert res.mimetype == "application/json"
    return body["error"]


def test_unhandled_exception_is_json_500_without_leaking(client, caplog):
    with caplog.at_level(logging.ERROR, logger="src.api"):
        res = client.get("/envtest/boom")
    assert res.status_code == 500
    err = _err(res)
    assert err["code"] == "INTERNAL"
    assert "secret internal detail" not in res.get_data(as_text=True)
    assert any("secret internal detail" in (r.exc_text or "") for r in caplog.records)


def test_404_in_view_is_envelope(client):
    res = client.get("/envtest/missing")
    assert res.status_code == 404
    assert _err(res)["code"] == "NOT_FOUND"


def test_400_keeps_description(client):
    res = client.get("/envtest/bad")
    assert res.status_code == 400
    err = _err(res)
    assert err["code"] == "BAD_REQUEST"
    assert err["message"] == "잘못된 요청"


def test_405_raised_in_view_is_envelope(client):
    res = client.get("/envtest/not-allowed")
    assert res.status_code == 405
    assert _err(res)["code"] == "METHOD_NOT_ALLOWED"


def test_routing_level_404_405_are_outside_blueprint_handlers(client):
    """Flask 제약 고정: 라우팅 단계 오류는 블루프린트 핸들러가 못 받는다(한계 문서화 — S3_results)."""
    res = client.get("/envtest/only-post")  # 라우트는 있으나 메서드 불일치
    assert res.status_code == 405
    assert res.get_json(silent=True) is None
    res = client.get("/envtest/nope")
    assert res.status_code == 404
    assert res.get_json(silent=True) is None


def test_413_is_envelope(client):
    res = client.post("/envtest/body", data="x" * 100, content_type="text/plain")
    assert res.status_code == 413
    assert _err(res)["code"] == "TOO_LARGE"


def test_unmapped_http_status_uses_name_as_code(client):
    res = client.get("/envtest/teapot")
    assert res.status_code == 418
    assert _err(res)["code"] == "I'M_A_TEAPOT"


def test_api_bp_has_the_shared_handlers():
    # api_bp 가 같은 함수로 등록됐는지(공용 등록, 복제 금지 — NEW-40)
    handlers = api_bp.error_handler_spec[None]
    assert Exception in handlers[None]
    from werkzeug.exceptions import HTTPException
    assert HTTPException in handlers[None]
