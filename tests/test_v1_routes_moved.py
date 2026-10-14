"""S3-7 (V1S-12 b) — v1 sync/import 라우트를 app.py → src/api/ 블루프린트로 옮긴 뒤에도
URL·메서드가 그대로이고, Origin 관문 예외(/api/garmin/local-sync)가 유지되는지 검증."""
from __future__ import annotations

from pathlib import Path

import pytest

from src.web.app import create_app

# 이동 전 app.py closure 라우트 (rule, methods)
EXPECTED = {
    ("/trigger-sync", "POST"),
    ("/trigger-sync-stream", "POST"),
    ("/trigger-sync-bg", "POST"),
    ("/api/garmin/local-sync", "POST"),
    ("/bg-sync/start", "POST"),
    ("/bg-sync/pause", "POST"),
    ("/bg-sync/stop", "POST"),
    ("/bg-sync/resume", "POST"),
    ("/bg-sync/status", "GET"),
    ("/import", "GET"),
    ("/import-preview", "GET"),
    ("/import/upload", "POST"),
    ("/import/upload-archive", "POST"),
    ("/sync-status", "GET"),
}


@pytest.fixture(scope="module")
def app():
    a = create_app()
    a.config["TESTING"] = True
    return a


def _routes(app):
    out = {}
    for r in app.url_map.iter_rules():
        for m in r.methods - {"HEAD", "OPTIONS"}:
            out[(r.rule, m)] = r.endpoint
    return out


def test_urls_and_methods_unchanged(app):
    routes = _routes(app)
    assert EXPECTED <= set(routes)


def test_owned_by_new_blueprints(app):
    routes = _routes(app)
    for key in EXPECTED:
        assert routes[key].startswith(("v1_sync.", "v1_pages.")), key
    assert {routes[k].split(".")[0] for k in EXPECTED} == {"v1_sync", "v1_pages"}


def test_no_duplicate_rules(app):
    seen = {}
    for r in app.url_map.iter_rules():
        for m in r.methods - {"HEAD", "OPTIONS"}:
            assert (r.rule, m) not in seen or seen[(r.rule, m)] == r.endpoint
            seen[(r.rule, m)] = r.endpoint


def test_app_py_has_no_moved_helpers():
    src = (Path(__file__).resolve().parent.parent / "src" / "web" / "app.py").read_text(encoding="utf-8")
    assert "_days_since_last_sync" not in src
    assert "_auto_match_after_sync" not in src
    assert "def trigger_sync" not in src
    assert "def bg_sync_" not in src


def test_garmin_local_sync_stays_origin_exempt(app):
    """토큰 기반 server-to-server 호출 — Origin 없이도 관문을 통과해야 한다(인증은 라우트 몫)."""
    with app.test_client() as c:
        r = c.post("/api/garmin/local-sync", json={})
    assert r.status_code != 403 or "FORBIDDEN_ORIGIN" not in r.get_data(as_text=True)


def test_trigger_sync_without_origin_is_rejected(app):
    with app.test_client() as c:
        r = c.post("/trigger-sync", data={"source": "garmin"})
    assert r.status_code == 403
