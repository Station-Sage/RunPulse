"""spa_static — `/v2/` 정적 서빙 분기·캐시 규칙·인라인 해시 (S3 7단계, E-04)."""
from __future__ import annotations

import base64
import hashlib
import os

import pytest
from flask import Flask

from src.web import spa_static
from src.web.spa_static import (
    cache_control_for, inline_script_hashes, resolve_v2, serve_v2_response,
)

INDEX = """<!doctype html><html><head>
<link rel="icon" href="/v2/favicon.ico">
</head><body>
<script>{ __sveltekit_abc = { base: "/v2" }; }</script>
<script type="module" src="/v2/_app/immutable/entry/start.js"></script>
<script type="application/json" data-sveltekit-fetched>{"a":1}</script>
<script>{ __sveltekit_abc = { base: "/v2" }; }</script>
<script type="module">import("/v2/x.js")</script>
</body></html>"""


def _sha(body: str) -> str:
    return "sha256-" + base64.b64encode(hashlib.sha256(body.encode()).digest()).decode()


@pytest.fixture
def build(tmp_path):
    b = tmp_path / "build"
    (b / "_app" / "immutable" / "entry").mkdir(parents=True)
    (b / "_app" / "immutable" / "entry" / "start.js").write_text("console.log(1)")
    (b / "_app" / "version.json").write_text('{"version":"1"}')
    (b / "index.html").write_text(INDEX, encoding="utf-8")
    (b / "favicon.ico").write_bytes(b"\x00\x00")
    (b / "robots.txt").write_text("User-agent: *")
    (b / "demo").mkdir()
    return b


@pytest.fixture
def client(build):
    app = Flask(__name__)

    @app.route("/v2/", defaults={"path": ""})
    @app.route("/v2/<path:path>")
    def v2(path):
        return serve_v2_response(build, path)

    with app.test_client() as c:
        yield c


# ── resolve_v2 ────────────────────────────────────────────────────────
def test_resolve_existing_file_is_asset(build):
    kind, f = resolve_v2(build, "_app/immutable/entry/start.js")
    assert kind == "asset" and f == build / "_app/immutable/entry/start.js"


@pytest.mark.parametrize("path", ["_app/immutable/x.js", "_app/nothing", "favicon.png", "a/b.css",
                                  "manifest.webmanifest", "x.JS", "chunk.js.map", "f.woff2", "data.json"])
def test_resolve_missing_asset(build, path):
    assert resolve_v2(build, path) == ("missing", None)


@pytest.mark.parametrize("path", ["", "today", "activity/2026.10.01", "coach/session.1", "demo", "a.b.c/d"])
def test_resolve_client_routes_are_spa(build, path):
    kind, f = resolve_v2(build, path)
    assert kind == "spa" and f == build / "index.html"


def test_resolve_never_serves_outside_build(build, tmp_path):
    (tmp_path / "secret.txt").write_text("s")
    assert resolve_v2(build, "../secret.txt")[0] == "spa"
    assert resolve_v2(build, "../secret.js")[0] == "missing"


# ── cache_control_for ────────────────────────────────────────────────
def test_cache_control_rules():
    assert "immutable" in cache_control_for("_app/immutable/chunks/a.js")
    assert "max-age=31536000" in cache_control_for("_app/immutable/chunks/a.js")
    assert cache_control_for("_app/version.json") == "no-cache"   # 근본 원인 2
    assert cache_control_for("favicon.ico") == "no-cache"
    assert cache_control_for("index.html") == "no-cache"
    assert cache_control_for("_app/immutablex/a.js") == "no-cache"


# ── 응답 (HTTP) ──────────────────────────────────────────────────────
def test_missing_immutable_asset_is_404_not_html(client):
    r = client.get("/v2/_app/immutable/x.js")
    assert r.status_code == 404
    assert r.headers["Cache-Control"] == "no-store"
    assert r.mimetype == "text/plain"
    assert b"<html" not in r.data


@pytest.mark.parametrize("url", ["/v2/today", "/v2/activity/2026.10.01", "/v2/", "/v2/demo"])
def test_deeplinks_return_index_html(client, url):
    r = client.get(url)
    assert r.status_code == 200 and b"__sveltekit_abc" in r.data
    assert r.headers["Cache-Control"] == "no-cache"
    r.close()


def test_immutable_asset_cached_one_year(client):
    r = client.get("/v2/_app/immutable/entry/start.js")
    assert r.status_code == 200
    assert r.headers["Cache-Control"] == "public, max-age=31536000, immutable"
    r.close()


def test_version_json_not_immutable(client):
    r = client.get("/v2/_app/version.json")
    assert r.status_code == 200 and r.headers["Cache-Control"] == "no-cache"
    r.close()


def test_favicon_200_when_present_404_when_absent(client, build):
    r = client.get("/v2/favicon.ico")
    assert r.status_code == 200
    r.close()
    (build / "favicon.ico").unlink()
    r = client.get("/v2/favicon.ico")
    assert r.status_code == 404 and b"<html" not in r.data


def test_no_build_dir_clientroute_404(tmp_path):
    """빌드 전(index.html 없음) — 기존처럼 404."""
    app = Flask(__name__)

    @app.route("/v2/<path:path>")
    def v2(path):
        return serve_v2_response(tmp_path / "nobuild", path)

    assert app.test_client().get("/v2/today").status_code == 404


# ── inline_script_hashes ─────────────────────────────────────────────
def test_hashes_inline_only_deduped_in_order(build):
    hs = inline_script_hashes(build / "index.html")
    assert hs == [_sha('{ __sveltekit_abc = { base: "/v2" }; }'), _sha('import("/v2/x.js")')]


def test_hashes_skip_external_and_json(build):
    hs = inline_script_hashes(build / "index.html")
    assert _sha('{"a":1}') not in hs


def test_hashes_missing_file(tmp_path):
    assert inline_script_hashes(tmp_path / "none.html") == []


def test_hashes_cached_by_mtime(build, monkeypatch):
    p = build / "index.html"
    spa_static._hash_cache.clear()
    first = inline_script_hashes(p)
    calls = []
    orig = type(p).read_text
    monkeypatch.setattr(type(p), "read_text", lambda self, *a, **k: calls.append(1) or orig(self, *a, **k))
    assert inline_script_hashes(p) == first
    assert calls == []          # 캐시 적중 — 파일을 다시 읽지 않음
    p.write_text("<script>var a=1</script>", encoding="utf-8")
    os.utime(p, ns=(1, 1))      # mtime 변경 → 무효화
    assert inline_script_hashes(p) == [_sha("var a=1")]
    assert calls == [1]


def test_hashes_returns_copy(build):
    a = inline_script_hashes(build / "index.html")
    a.append("x")
    assert "x" not in inline_script_hashes(build / "index.html")


def test_real_app_serve_v2_delegates(monkeypatch, tmp_path):
    """create_app 의 /v2/ 라우트가 spa_static 으로 위임되는지(없는 자산 404)."""
    from src.web.app import create_app
    app = create_app()
    with app.test_client() as c:
        r = c.get("/v2/_app/immutable/definitely-missing.js")
    assert r.status_code == 404 and r.headers["Cache-Control"] == "no-store"
