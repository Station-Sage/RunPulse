"""response_policy — 공통 보안 헤더·표면별 CSP (S3 8단계, E-01, ADR-049)."""
from __future__ import annotations

import pytest
from flask import Flask, Response

from src.web import response_policy as rp
from src.web.response_policy import (
    apply_policy, build_csp, classify_surface, common_headers, csp_header_for, csp_v2_mode,
    init_response_policy,
)

H = "sha256-JVOU8BoHKjyaIlnTFSejtb3+Jk36+hOr72OhOiFsK0c="


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv("CSP_V2_MODE", raising=False)


# ── classify_surface ─────────────────────────────────────────────────
@pytest.mark.parametrize("path,surface", [
    ("/v2/", "v2"), ("/v2", "v2"), ("/v2/today", "v2"), ("/v2/_app/x.js", "v2"),
    ("/api/v1/today", "api"), ("/api/context-episodes", "api"),          # NEW-40: /api/v1 접두 의존 금지
    ("/api/garmin/local-sync", "api"), ("/mcp", "api"), ("/mcp/", "api"),
    ("/feeds/cal/tok.ics", "feed"),
    ("/", "default"), ("/trigger-sync", "default"), ("/bg-sync/status", "default"),
    ("/sync-status", "default"), ("/import", "default"), ("/nope", "default"),
    ("/v2x/a", "default"), ("/apix", "default"), ("/mcpx", "default"), ("/feedsx", "default"),  # 접두 경계
])
def test_classify_surface(path, surface):
    assert classify_surface(path) == surface


def test_no_v1_surface():
    """V1-15 — 'v1' 표면 없음."""
    assert {classify_surface(p) for p in ("/", "/activities", "/settings", "/trigger-sync")} == {"default"}


# ── build_csp ────────────────────────────────────────────────────────
def test_csp_api_and_feed_strictest():
    for s in ("api", "feed"):
        assert build_csp(s) == "default-src 'none'; frame-ancestors 'none'"


def test_csp_v2_has_hash_and_required_directives():
    csp = build_csp("v2", [H])
    assert f"script-src 'self' '{H}'" in csp
    for d in ("default-src 'self'", "style-src 'self' 'unsafe-inline'", "img-src 'self' data:", "connect-src 'self'",
              "base-uri 'self'", "form-action 'self'", "object-src 'none'", "frame-ancestors 'none'",
              "report-uri /api/v1/csp-report"):
        assert d in csp
    assert "unsafe-eval" not in csp and "script-src 'self' 'unsafe-inline'" not in csp


def test_csp_default_surface_ignores_hashes():
    """SEC-12 (a) — 일반 표면은 인라인 해시 미포함(엄격)."""
    csp = build_csp("default", [H])
    assert "sha256" not in csp
    assert "script-src 'self';" in csp
    assert "frame-ancestors 'none'" in csp and "report-uri /api/v1/csp-report" in csp


def test_csp_v2_without_hashes_has_plain_self():
    assert "script-src 'self';" in build_csp("v2", [])


@pytest.mark.parametrize("bad", ["sha256-abc'; script-src *", "'unsafe-inline'", "sha256-a b", "", "md5-AAAA", "sha256-"])
def test_csp_drops_non_hash_tokens(bad):
    csp = build_csp("v2", [bad, H])
    assert csp.count("sha256-") == 1 and H in csp and "script-src *" not in csp


def test_csp_unknown_surface_raises():
    with pytest.raises(ValueError):
        build_csp("v1")


# ── 공통 헤더·모드 ───────────────────────────────────────────────────
def test_common_headers_content():
    h = common_headers()
    assert h["X-Content-Type-Options"] == "nosniff"
    assert h["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert h["X-Frame-Options"] == "DENY"
    assert h["Permissions-Policy"] == "camera=(), microphone=(), geolocation=()"
    assert "Strict-Transport-Security" not in h            # D4
    assert "Cross-Origin-Opener-Policy" not in h           # D9


def test_common_headers_returns_copy():
    common_headers()["X-Frame-Options"] = "x"
    assert common_headers()["X-Frame-Options"] == "DENY"


def test_mode_default_and_values(monkeypatch):
    assert csp_v2_mode() == "report-only"
    monkeypatch.setenv("CSP_V2_MODE", " ENFORCE ")
    assert csp_v2_mode() == "enforce"


def test_mode_unknown_falls_back_to_report_only(monkeypatch, caplog):
    monkeypatch.setenv("CSP_V2_MODE", "block")
    with caplog.at_level("WARNING", logger="runpulse.security"):
        assert csp_v2_mode() == "report-only"
    assert "CSP_V2_MODE" in caplog.text


@pytest.mark.parametrize("surface,mode,header", [
    ("v2", "report-only", "Content-Security-Policy-Report-Only"),
    ("default", "report-only", "Content-Security-Policy-Report-Only"),
    ("v2", "enforce", "Content-Security-Policy"),
    ("default", "enforce", "Content-Security-Policy"),
    ("api", "report-only", "Content-Security-Policy"),      # api/feed 는 모드와 무관하게 enforce
    ("feed", "report-only", "Content-Security-Policy"),
])
def test_csp_header_for(surface, mode, header):
    assert csp_header_for(surface, mode) == header


# ── 앱 통합 ──────────────────────────────────────────────────────────
@pytest.fixture
def app(tmp_path):
    index = tmp_path / "index.html"
    index.write_text("<html><script>var boot=1</script></html>", encoding="utf-8")
    a = Flask(__name__)
    a.config["V2_INDEX_HTML"] = index
    init_response_policy(a)

    @a.get("/v2/today")
    def v2():
        return "x"

    @a.get("/api/v1/x")
    def api():
        return {"a": 1}

    @a.get("/api/context-episodes")
    def ctx():
        return {"a": 1}

    @a.get("/feeds/cal/t.ics")
    def feed():
        return Response("BEGIN", headers={"Cache-Control": "no-store"})

    @a.get("/legacy")
    def legacy():
        return "<html>"

    @a.get("/api/v1/stream")
    def sse():
        return Response("data: 1\n\n", mimetype="text/event-stream",
                        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    @a.get("/api/v1/own-csp")
    def own():
        return Response("x", headers={"Content-Security-Policy": "default-src 'self'", "X-Frame-Options": "SAMEORIGIN"})

    return a


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.mark.parametrize("url", ["/v2/today", "/api/v1/x", "/api/context-episodes", "/feeds/cal/t.ics", "/legacy", "/missing"])
def test_all_surfaces_get_common_headers(client, url):
    r = client.get(url)
    for k, v in common_headers().items():
        assert r.headers[k] == v, (url, k)
    assert "Strict-Transport-Security" not in r.headers


def test_404_and_errors_also_covered(client):
    r = client.get("/api/v1/does-not-exist")
    assert r.status_code == 404 and r.headers["X-Frame-Options"] == "DENY"
    assert r.headers["Content-Security-Policy"] == "default-src 'none'; frame-ancestors 'none'"


def test_v2_report_only_with_hash_from_index(client):
    r = client.get("/v2/today")
    assert "Content-Security-Policy" not in r.headers
    csp = r.headers["Content-Security-Policy-Report-Only"]
    assert "script-src 'self' 'sha256-" in csp


def test_v2_enforce_switches_header(client, monkeypatch):
    monkeypatch.setenv("CSP_V2_MODE", "enforce")
    r = client.get("/v2/today")
    assert "Content-Security-Policy-Report-Only" not in r.headers
    assert "script-src 'self' 'sha256-" in r.headers["Content-Security-Policy"]


def test_default_surface_follows_mode_and_has_no_hash(client, monkeypatch):
    r = client.get("/legacy")
    assert "sha256" not in r.headers["Content-Security-Policy-Report-Only"]
    monkeypatch.setenv("CSP_V2_MODE", "enforce")
    r = client.get("/legacy")
    assert "sha256" not in r.headers["Content-Security-Policy"]
    assert "Content-Security-Policy-Report-Only" not in r.headers


@pytest.mark.parametrize("url", ["/api/v1/x", "/api/context-episodes", "/feeds/cal/t.ics"])
def test_api_feed_always_enforced_strict(client, url, monkeypatch):
    for mode in ("report-only", "enforce"):
        monkeypatch.setenv("CSP_V2_MODE", mode)
        r = client.get(url)
        assert r.headers["Content-Security-Policy"] == "default-src 'none'; frame-ancestors 'none'"
        assert "Content-Security-Policy-Report-Only" not in r.headers


def test_route_headers_preserved(client):
    r = client.get("/feeds/cal/t.ics")
    assert r.headers["Cache-Control"] == "no-store"
    r = client.get("/api/v1/stream")
    assert r.headers["Cache-Control"] == "no-cache" and r.headers["X-Accel-Buffering"] == "no"
    assert r.headers["X-Frame-Options"] == "DENY"
    r.close()


def test_route_set_csp_and_xfo_not_overwritten(client):
    r = client.get("/api/v1/own-csp")
    assert r.headers["Content-Security-Policy"] == "default-src 'self'"
    assert r.headers["X-Frame-Options"] == "SAMEORIGIN"
    assert "Content-Security-Policy-Report-Only" not in r.headers


def test_missing_index_html_gives_plain_self(tmp_path):
    a = Flask(__name__)
    a.config["V2_INDEX_HTML"] = tmp_path / "none.html"
    init_response_policy(a)
    a.add_url_rule("/v2/x", "x", lambda: "x")
    r = a.test_client().get("/v2/x")
    assert "script-src 'self';" in r.headers["Content-Security-Policy-Report-Only"]


def test_apply_policy_direct():
    r = apply_policy(Response("x"), "/api/v1/a")
    assert r.headers["Content-Security-Policy"].startswith("default-src 'none'")


# ── 실제 앱 통합 (기존 Cache-Control·보호 경로 회귀) ─────────────────
def test_real_app_surfaces():
    from src.web.app import create_app
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        for url, hdr in [("/v2/today", "Content-Security-Policy-Report-Only"),
                         ("/api/v1/today", "Content-Security-Policy"),
                         ("/mcp", "Content-Security-Policy"),
                         ("/feeds/cal/zzz.ics", "Content-Security-Policy"),
                         ("/nope", "Content-Security-Policy-Report-Only")]:
            r = c.get(url)
            assert hdr in r.headers and r.headers["X-Frame-Options"] == "DENY", url
            r.close()


def test_real_app_v2_asset_keeps_cache_control():
    from src.web.app import create_app
    with create_app().test_client() as c:
        r = c.get("/v2/_app/immutable/nope.js")
    assert r.status_code == 404 and r.headers["Cache-Control"] == "no-store"
    assert r.headers["X-Content-Type-Options"] == "nosniff"
