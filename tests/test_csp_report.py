"""POST /api/v1/csp-report — 로그 전용 보고 수신 (S3 8단계, SRV-12·SEC-12)."""
from __future__ import annotations

import json
import logging

import pytest

from src.api import routes_csp_report as rc
from src.web.app import create_app

LEGACY = {"csp-report": {
    "document-uri": "https://x.example/v2/today?token=SECRET#frag", "effective-directive": "script-src-elem",
    "blocked-uri": "inline", "source-file": "https://x.example/v2/a.js?k=SECRET", "line-number": 7,
    "disposition": "report"}}
REPORTING = [{"type": "csp-violation", "url": "https://x.example/v2/today", "body": {
    "effectiveDirective": "img-src", "blockedURL": "https://evil.example/p.png", "sourceFile": None,
    "documentURL": "https://x.example/v2/today", "lineNumber": 3, "disposition": "report"}}]


@pytest.fixture(scope="module")
def app():
    a = create_app()
    a.config["TESTING"] = True
    return a


@pytest.fixture
def client(app):
    with app.test_client() as c:
        yield c


def post(client, body, ctype="application/csp-report", **kw):
    data = body if isinstance(body, (bytes, str)) else json.dumps(body)
    return client.post("/api/v1/csp-report", data=data, content_type=ctype, **kw)


def lines(caplog):
    return [r.getMessage() for r in caplog.records if r.name == "runpulse.csp"]


# ── 204 · 면제 ────────────────────────────────────────────────────────
def test_legacy_report_204_without_origin(client, caplog):
    """Origin 없이도 통과(관문 면제, enforce 모드 — conftest) · 415 아님(SRV-12)."""
    with caplog.at_level(logging.INFO, logger="runpulse.csp"):
        r = post(client, LEGACY)
    assert r.status_code == 204 and r.data == b""
    assert any("ext=0" in l and "script-src-elem" in l for l in lines(caplog))


def test_reporting_api_format_204(client, caplog):
    with caplog.at_level(logging.INFO, logger="runpulse.csp"):
        r = post(client, REPORTING, "application/reports+json")
    assert r.status_code == 204
    assert any("ext=0" in l and "img-src" in l and "evil.example" in l for l in lines(caplog))


def test_charset_in_content_type_ok(client, caplog):
    with caplog.at_level(logging.INFO, logger="runpulse.csp"):
        r = post(client, LEGACY, "application/csp-report; charset=utf-8")
    assert r.status_code == 204 and any("ext=0" in l for l in lines(caplog))


def test_exempt_from_origin_gate_but_other_post_is_not(client):
    assert post(client, LEGACY).status_code == 204
    r = client.post("/api/v1/dev/switch-user", json={"user_id": "a"})   # Origin 없음 → 관문이 막는다
    assert r.status_code == 403 and r.get_json()["error"]["code"] == "FORBIDDEN_ORIGIN"


def test_get_not_allowed(client):
    assert client.get("/api/v1/csp-report").status_code == 405


# ── 수용 형식 밖 → 204 + 로그 ─────────────────────────────────────────
@pytest.mark.parametrize("ctype", ["application/json", "text/plain", "application/x-www-form-urlencoded"])
def test_wrong_content_type_204_logged(client, caplog, ctype):
    with caplog.at_level(logging.INFO, logger="runpulse.csp"):
        r = post(client, LEGACY, ctype)
    assert r.status_code == 204
    assert any("unaccepted reason=content-type" in l for l in lines(caplog))
    assert not any("ext=0" in l for l in lines(caplog))


def test_no_content_type_204(client, caplog):
    with caplog.at_level(logging.INFO, logger="runpulse.csp"):
        r = client.post("/api/v1/csp-report", data=b"{}")
    assert r.status_code == 204


@pytest.mark.parametrize("body", [b"not json", b"\xff\xfe", b"", b"[]", b'{"csp-report": 1}', b'{"x":1}', b"null"])
def test_unparsable_204_logged(client, caplog, body):
    with caplog.at_level(logging.INFO, logger="runpulse.csp"):
        r = post(client, body)
    assert r.status_code == 204
    assert any("unaccepted reason=unparsable" in l for l in lines(caplog))


def test_reporting_api_non_csp_types_ignored(client, caplog):
    with caplog.at_level(logging.INFO, logger="runpulse.csp"):
        r = post(client, [{"type": "deprecation", "body": {}}, "x", 3], "application/reports+json")
    assert r.status_code == 204 and any("unparsable" in l for l in lines(caplog))


def test_oversize_body_204_logged_not_parsed(client, caplog):
    big = json.dumps({"csp-report": {"blocked-uri": "x" * (rc.MAX_BYTES + 10)}})
    with caplog.at_level(logging.INFO, logger="runpulse.csp"):
        r = post(client, big)
    assert r.status_code == 204
    assert any("too-large" in l for l in lines(caplog))
    assert not any("ext=" in l for l in lines(caplog))


def test_body_at_limit_is_accepted(client, caplog):
    pad = json.dumps({"csp-report": {"blocked-uri": "inline", "effective-directive": "d", "pad": ""}})
    body = pad.replace('"pad": ""', '"pad": "' + "a" * (rc.MAX_BYTES - len(pad)) + '"')
    assert len(body.encode()) == rc.MAX_BYTES
    with caplog.at_level(logging.INFO, logger="runpulse.csp"):
        assert post(client, body).status_code == 204
    assert any("ext=0" in l for l in lines(caplog))


# ── 확장 프로그램 잡음 ────────────────────────────────────────────────
@pytest.mark.parametrize("scheme", ["chrome-extension", "moz-extension", "safari-web-extension", "safari-extension"])
def test_extension_scheme_flagged_and_excluded(client, caplog, scheme):
    rep = {"csp-report": {"blocked-uri": f"{scheme}://abc/x.js", "effective-directive": "script-src-elem"}}
    with caplog.at_level(logging.INFO, logger="runpulse.csp"):
        assert post(client, rep).status_code == 204
    ls = lines(caplog)
    assert any("ext=1" in l for l in ls) and not any("ext=0" in l for l in ls)


def test_inline_blocked_judged_by_source_file(client, caplog):
    """blocked=inline 이어도 source-file 이 확장 프로그램이면 제외(SEC-12)."""
    rep = {"csp-report": {"blocked-uri": "inline", "source-file": "chrome-extension://abc/c.js", "effective-directive": "d"}}
    with caplog.at_level(logging.INFO, logger="runpulse.csp"):
        post(client, rep)
    assert any("ext=1" in l for l in lines(caplog))


def test_extension_logged_below_warning_real_violation_at_warning(client, caplog):
    with caplog.at_level(logging.INFO, logger="runpulse.csp"):
        post(client, {"csp-report": {"blocked-uri": "moz-extension://a/b", "effective-directive": "d"}})
        post(client, LEGACY)
    lv = {("ext=1" in r.getMessage()): r.levelno for r in caplog.records if r.name == "runpulse.csp" and "ext=" in r.getMessage()}
    assert lv[True] == logging.INFO and lv[False] == logging.WARNING


def test_is_extension_unit():
    assert rc.is_extension("", "moz-extension://x")
    assert rc.is_extension("CHROME-EXTENSION://x", "")
    assert not rc.is_extension("inline", "")
    assert not rc.is_extension("https://chrome-extension.example/x", "")


# ── 로그 안전 ─────────────────────────────────────────────────────────
def test_query_and_fragment_stripped_from_logs(client, caplog):
    with caplog.at_level(logging.INFO, logger="runpulse.csp"):
        post(client, LEGACY)
    assert "SECRET" not in caplog.text and "frag" not in caplog.text


def test_fields_truncated_and_non_str_safe(client, caplog):
    rep = {"csp-report": {"blocked-uri": "h" * 5000, "effective-directive": 12, "line-number": "x", "source-file": ["a"],
                          "disposition": {"a": 1}}}
    with caplog.at_level(logging.INFO, logger="runpulse.csp"):
        assert post(client, rep).status_code == 204
    assert max(len(l) for l in lines(caplog)) < 1200
    assert "line=0" in " ".join(lines(caplog))


def test_newline_injection_stays_in_one_record(client, caplog):
    rep = {"csp-report": {"blocked-uri": "x\n[csp-report] ext=1 forged", "effective-directive": "d"}}
    with caplog.at_level(logging.INFO, logger="runpulse.csp"):
        post(client, rep)
    ls = lines(caplog)
    assert len(ls) == 1 and "\n" not in ls[0]      # %r 이라 개행이 이스케이프됨


def test_report_count_capped(client, caplog):
    items = [{"type": "csp-violation", "body": {"effectiveDirective": "d", "blockedURL": f"u{i}"}} for i in range(50)]
    with caplog.at_level(logging.INFO, logger="runpulse.csp"):
        assert post(client, items, "application/reports+json").status_code == 204
    ls = lines(caplog)
    assert sum("ext=0" in l for l in ls) == rc.MAX_REPORTS and any("truncated extra=40" in l for l in ls)


def test_not_enveloped_and_has_security_headers(client):
    r = post(client, LEGACY)
    assert r.status_code == 204 and r.headers["X-Frame-Options"] == "DENY"
    assert r.headers["Content-Security-Policy"].startswith("default-src 'none'")


def test_parse_reports_unit():
    assert rc.parse_reports("application/csp-report", json.dumps(LEGACY).encode())[0]["directive"] == "script-src-elem"
    assert rc.parse_reports("application/reports+json", json.dumps(REPORTING).encode())[0]["blocked"].startswith("https://evil")
    assert rc.parse_reports("application/csp-report", b"zz") == []
