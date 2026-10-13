"""tests/test_request_guard.py — Origin 관문·봉투 403·쿠키 속성 (SRV 2.1, ADR-048 4단계).

최소 Flask 앱에 `init_request_guard` 만 붙여 관문 로직을 검증하고,
쿠키 속성은 실제 `create_app` 조립으로 확인한다.
"""
from __future__ import annotations

import logging

import pytest
from flask import Flask

from src.web import request_guard as rg

BASE = "https://run.example.com"
PATHS = [
    "/form", "/api/v1/things", "/api/context-episodes", "/api/context-episodes/7",
    "/mcp", "/api/garmin/local-sync", "/feeds/cal/abc.ics", "/api/v1/csp-report",
]


def _make_app() -> Flask:
    app = Flask(__name__)
    app.config["TESTING"] = True

    def ok(*_a, **_k):
        return "ok"

    methods = ["GET", "POST", "PUT", "PATCH", "DELETE"]
    for i, p in enumerate(PATHS):
        app.add_url_rule(p, f"r{i}", ok, methods=methods)
    app.add_url_rule("/api/context-episodes/<int:n>", "ep_n", ok, methods=methods)
    rg.init_request_guard(app)
    return app


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv("PUBLIC_BASE_URL", BASE)
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("ORIGIN_GUARD_MODE", raising=False)


@pytest.fixture
def enforce(env, monkeypatch):
    monkeypatch.setenv("ORIGIN_GUARD_MODE", "enforce")


@pytest.fixture
def client(env):
    return _make_app().test_client()


# ── same_origin / 출처 판정 ────────────────────────────────────────────

def test_same_origin_accepts_public_base(enforce, client):
    assert client.post("/form", headers={"Origin": BASE}).status_code == 200


def test_origin_case_and_default_port_forms(enforce, client):
    assert client.post("/form", headers={"Origin": "HTTPS://RUN.EXAMPLE.COM"}).status_code == 200
    assert client.post("/form", headers={"Origin": "https://run.example.com:8443"}).status_code == 403


def test_forged_origin_rejected(enforce, client):
    assert client.post("/form", headers={"Origin": "https://evil.example"}).status_code == 403


def test_null_origin_rejected(enforce, client):
    assert client.post("/form", headers={"Origin": "null"}).status_code == 403


def test_lookalike_origin_rejected(enforce, client):
    for o in ("https://run.example.com.evil.example", "http://run.example.com"):
        assert client.post("/form", headers={"Origin": o}).status_code == 403


def test_referer_fallback_when_origin_absent(enforce, client):
    assert client.post("/form", headers={"Referer": BASE + "/v2/today?x=1"}).status_code == 200
    assert client.post("/form", headers={"Referer": "https://evil.example/v2"}).status_code == 403


def test_origin_wins_over_referer(enforce, client):
    h = {"Origin": "https://evil.example", "Referer": BASE + "/v2"}
    assert client.post("/form", headers=h).status_code == 403


def test_both_missing_rejected(enforce, client):
    assert client.post("/form").status_code == 403


def test_garbage_referer_rejected(enforce, client):
    assert client.post("/form", headers={"Referer": "/v2/today"}).status_code == 403


def test_get_is_never_checked(enforce, client):
    assert client.get("/form").status_code == 200
    assert client.get("/form", headers={"Origin": "https://evil.example"}).status_code == 200


@pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
def test_all_state_changing_methods_checked(enforce, client, method):
    assert getattr(client, method)("/form", headers={"Origin": "https://evil.example"}).status_code == 403
    assert getattr(client, method)("/form", headers={"Origin": BASE}).status_code == 200


def test_dev_origins_only_outside_production(enforce, client, monkeypatch):
    h = {"Origin": "http://localhost:5173"}
    assert client.post("/form", headers=h).status_code == 200
    monkeypatch.setenv("APP_ENV", "production")
    assert client.post("/form", headers=h).status_code == 403


def test_base_url_fallback_is_request_root(enforce, monkeypatch):
    """PUBLIC_BASE_URL 이 없으면 요청 url_root 가 기준(개발 편의) — Host 헤더 위조는 그 요청의 Host 로만 통한다."""
    monkeypatch.delenv("PUBLIC_BASE_URL")
    c = _make_app().test_client()
    assert c.post("/form", headers={"Origin": "http://localhost"}).status_code == 200
    assert c.post("/form", headers={"Origin": "http://evil.example"}).status_code == 403


# ── 면제 경로 ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("path", ["/mcp", "/api/garmin/local-sync", "/feeds/cal/abc.ics", "/api/v1/csp-report"])
def test_exempt_paths_pass_without_origin(enforce, client, path):
    assert client.post(path).status_code == 200
    assert client.post(path, headers={"Origin": "https://evil.example"}).status_code == 200


def test_context_episodes_is_not_exempt(enforce, client):
    assert not rg.is_exempt("/api/context-episodes")
    assert not rg.is_exempt("/api/context-episodes/7")
    assert client.post("/api/context-episodes").status_code == 403
    assert client.delete("/api/context-episodes/7", headers={"Origin": "https://evil.example"}).status_code == 403


def test_exempt_matching_is_boundary_safe():
    assert rg.is_exempt("/mcp") and rg.is_exempt("/mcp/")
    assert not rg.is_exempt("/mcpx")
    assert not rg.is_exempt("/api/garmin/local-sync-evil")
    assert not rg.is_exempt("/feeds/cal")  # 접두는 `/feeds/cal/` 만
    assert "/api/context-episodes" not in rg.EXEMPT_PATHS


# ── 거부 응답 형식 ────────────────────────────────────────────────────

@pytest.mark.parametrize("path", ["/api/v1/things", "/api/context-episodes", "/api/context-episodes/7"])
def test_envelope_paths_get_json_403(enforce, client, path):
    r = client.post(path, headers={"Origin": "https://evil.example"})
    assert r.status_code == 403
    assert r.is_json
    err = r.get_json()["error"]
    assert err["code"] == "FORBIDDEN_ORIGIN" and err["message"]


def test_other_paths_get_text_403(enforce, client):
    r = client.post("/form", headers={"Origin": "https://evil.example"})
    assert r.status_code == 403
    assert r.mimetype == "text/plain"
    assert "FORBIDDEN_ORIGIN" not in r.get_data(as_text=True)


# ── observe 모드 ──────────────────────────────────────────────────────

def test_observe_is_default_and_passes_through_with_log(client, caplog):
    assert rg.guard_mode() == "observe"
    with caplog.at_level(logging.WARNING, logger="runpulse.security"):
        r = client.post("/form", headers={"Origin": "https://evil.example", "Referer": "https://evil.example/x"})
    assert r.status_code == 200
    rec = [x for x in caplog.records if "origin_guard" in x.getMessage()]
    assert len(rec) == 1
    msg = rec[0].getMessage()
    assert "mode=observe" in msg and "POST" in msg and "/form" in msg and "evil.example" in msg


def test_observe_logs_missing_origin_and_referer(client, caplog):
    with caplog.at_level(logging.WARNING, logger="runpulse.security"):
        assert client.post("/api/v1/things").status_code == 200
    assert any("origin=None" in x.getMessage() and "referer=None" in x.getMessage() for x in caplog.records)


def test_no_log_for_valid_exempt_or_get(client, caplog):
    with caplog.at_level(logging.WARNING, logger="runpulse.security"):
        client.post("/form", headers={"Origin": BASE})
        client.post("/mcp")
        client.get("/form")
    assert not [x for x in caplog.records if "origin_guard" in x.getMessage()]


def test_enforce_also_logs(enforce, client, caplog):
    with caplog.at_level(logging.WARNING, logger="runpulse.security"):
        client.post("/form", headers={"Origin": "https://evil.example"})
    assert any("mode=enforce" in x.getMessage() for x in caplog.records)


@pytest.mark.parametrize("raw,expected", [("", "observe"), ("ENFORCE", "enforce"), (" enforce ", "enforce"),
                                          ("observe", "observe"), ("bogus", "observe")])
def test_mode_parsing_falls_back_to_observe(env, monkeypatch, raw, expected):
    monkeypatch.setenv("ORIGIN_GUARD_MODE", raw)
    assert rg.guard_mode() == expected


def test_production_without_public_base_url_warns(env, monkeypatch, caplog):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("PUBLIC_BASE_URL")
    with caplog.at_level(logging.WARNING, logger="runpulse.security"):
        rg.init_request_guard(Flask(__name__))
    assert any("PUBLIC_BASE_URL" in x.getMessage() for x in caplog.records)


# ── 쿠키 속성 / 실제 앱 조립 ──────────────────────────────────────────

def _create(tmp_path, monkeypatch, app_env):
    from src.web.app import create_app
    import src.db_setup as dbs
    monkeypatch.setenv("FLASK_SECRET_KEY", "k")
    monkeypatch.setenv("APP_ENV", app_env)
    monkeypatch.setattr(dbs, "_PROJECT_ROOT", tmp_path)  # 실제 data/users 격리
    return create_app()


@pytest.mark.parametrize("app_env,secure", [("development", False), ("production", True)])
def test_session_cookie_config_per_app_env(tmp_path, monkeypatch, app_env, secure):
    app = _create(tmp_path, monkeypatch, app_env)
    assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"
    assert app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert app.config["SESSION_COOKIE_SECURE"] is secure


def test_create_app_registers_guard_and_enforces(tmp_path, monkeypatch):
    monkeypatch.setenv("PUBLIC_BASE_URL", BASE)
    monkeypatch.setenv("ORIGIN_GUARD_MODE", "enforce")
    app = _create(tmp_path, monkeypatch, "development")
    app.config["TESTING"] = True
    hdr = {"CF-Access-Authenticated-User-Email": "ok@example.com"}
    with app.test_client() as c:
        bad = c.post("/api/v1/today/checkin", json={"fatigue": 3}, headers={**hdr, "Origin": "https://evil.example"})
        assert bad.status_code == 403
        assert bad.get_json()["error"]["code"] == "FORBIDDEN_ORIGIN"
        good = c.post("/api/v1/today/checkin", json={"fatigue": 3}, headers={**hdr, "Origin": BASE})
        assert good.status_code != 403
