"""frontend/static 의 favicon·manifest·apple-touch-icon 자산 정합성 (S3 9단계, SEC-7/D7).

빌드(`frontend/build`)는 git 에 없으므로 소스 `frontend/static` 과 `app.html` 을 검사하고,
`serve_v2_response` 로 이 디렉터리를 서빙해 200 인지 확인한다."""
from __future__ import annotations

import json
import math
import re
import struct
from pathlib import Path

import pytest
from flask import Flask

from src.web.spa_static import serve_v2_response

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "frontend" / "static"
APP_HTML = ROOT / "frontend" / "src" / "app.html"
MANIFEST = STATIC / "manifest.webmanifest"


@pytest.fixture(scope="module")
def manifest():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


@pytest.fixture
def client():
    app = Flask(__name__)

    @app.route("/v2/<path:path>")
    def v2(path):
        return serve_v2_response(STATIC, path)

    with app.test_client() as c:
        yield c


def png_size(path: Path) -> tuple[int, int]:
    """PNG IHDR 에서 (width, height) — Pillow 없이 표준 라이브러리만 사용."""
    head = path.read_bytes()[:24]
    assert head[:8] == b"\x89PNG\r\n\x1a\n" and head[12:16] == b"IHDR", path
    return struct.unpack(">II", head[16:24])


def _local(src: str) -> Path:
    assert src.startswith("/v2/"), src            # base path('/v2') 아래여야 Flask 가 서빙한다
    return STATIC / src[len("/v2/"):]


def test_manifest_basics(manifest):
    assert manifest["short_name"] == "RunPulse" and manifest["lang"] == "ko"
    assert manifest["display"] == "standalone"
    assert manifest["start_url"].startswith("/v2/") and manifest["scope"] == "/v2/"
    assert manifest["start_url"].startswith(manifest["scope"])


def test_manifest_colors_match_dark_s1_token(manifest):
    """accessibility-common §2.5 — manifest theme_color 는 다크 s1(#0f172a) 단일 값."""
    css = (ROOT / "frontend" / "src" / "routes" / "layout.css").read_text(encoding="utf-8")
    s1 = re.search(r"--color-surface-1:\s*(#[0-9a-fA-F]{6})", css).group(1).lower()
    assert manifest["theme_color"].lower() == s1 and manifest["background_color"].lower() == s1


def test_manifest_icons_exist_and_sizes_match(manifest):
    assert {i["purpose"] for i in manifest["icons"]} >= {"any", "maskable"}
    for icon in manifest["icons"]:
        p = _local(icon["src"])
        assert p.is_file(), icon["src"]
        w, h = png_size(p)
        assert icon["sizes"] == f"{w}x{h}" and icon["type"] == "image/png"
    assert {i["sizes"] for i in manifest["icons"]} >= {"192x192", "512x512"}


def test_maskable_glyph_inside_safe_zone(manifest):
    """maskable 은 중심 지름 80% 원 안에 글리프가 있어야 잘리지 않는다. (픽셀 검사 — Pillow 필요)"""
    Image = pytest.importorskip("PIL.Image")
    for icon in (i for i in manifest["icons"] if i["purpose"] == "maskable"):
        im = Image.open(_local(icon["src"])).convert("RGB")
        w, h = im.size
        px = im.load()
        far = max((math.hypot(x - w / 2, y - h / 2) for y in range(0, h, 2) for x in range(0, w, 2) if min(px[x, y]) < 200), default=0)
        assert far <= 0.4 * w, (icon["src"], far)


def test_icons_are_opaque_not_fake_checkerboard():
    """v1 의 `icon-*.png` 는 체커보드 '투명' 무늬가 픽셀로 박혀 있다 — v2 자산은 흰 바탕이어야 한다. (Pillow 필요)"""
    Image = pytest.importorskip("PIL.Image")
    for p in (STATIC / "icons").glob("*.png"):
        im = Image.open(p).convert("RGB")
        assert min(im.getpixel((2, 2))) >= 240, p.name


def test_apple_touch_icon_180():
    p = STATIC / "apple-touch-icon.png"
    assert png_size(p) == (180, 180)


def test_favicon_is_real_ico_with_small_sizes():
    data = (STATIC / "favicon.ico").read_bytes()
    reserved, kind, count = struct.unpack("<HHH", data[:6])
    assert (reserved, kind) == (0, 1) and count >= 2
    sizes = {(data[6 + 16 * i] or 256) for i in range(count)}
    assert {16, 32} <= sizes


def test_app_html_links_and_no_theme_color():
    html = APP_HTML.read_text(encoding="utf-8")
    assert 'rel="icon" href="%sveltekit.assets%/favicon.ico"' in html
    assert 'rel="apple-touch-icon" href="%sveltekit.assets%/apple-touch-icon.png"' in html
    assert 'rel="manifest" href="%sveltekit.assets%/manifest.webmanifest"' in html
    # CF Access 뒤에서 manifest 요청에 쿠키가 실려야 302 로 막히지 않는다
    assert re.search(r'rel="manifest"[^>]*crossorigin="use-credentials"', html)
    assert not re.search(r'<meta[^>]*name="theme-color"', html)   # A11Y §2.5 단일 소유 — 이 단계에서 넣지 않는다


@pytest.mark.parametrize("name,mime", [
    ("favicon.ico", "image/vnd.microsoft.icon"),
    ("apple-touch-icon.png", "image/png"),
    ("manifest.webmanifest", "application/manifest+json"),
    ("icons/icon-192.png", "image/png"),
    ("icons/icon-512.png", "image/png"),
])
def test_served_200_with_revalidation(client, name, mime):
    r = client.get(f"/v2/{name}")
    assert r.status_code == 200 and r.mimetype == mime
    assert r.headers["Cache-Control"] == "no-cache"
    r.close()


def test_unknown_icon_still_404(client):
    r = client.get("/v2/icons/icon-1024.png")
    assert r.status_code == 404 and r.headers["Cache-Control"] == "no-store"


def test_hooks_client_wiring_present():
    """오래된 탭 복구 배선 — 자동 새로고침 호출이 없어야 한다(SEC-8 (b))."""
    hooks = (ROOT / "frontend" / "src" / "hooks.client.ts").read_text(encoding="utf-8")
    assert "vite:preloadError" in hooks and "preventDefault" in hooks and "updated.check" in hooks
    code = "\n".join(l for l in hooks.splitlines() if not l.lstrip().startswith("//"))
    assert "location.reload" not in code and "invalidateAll" not in code
    layout = (ROOT / "frontend" / "src" / "routes" / "+layout.svelte").read_text(encoding="utf-8")
    assert "<UpdateNotice />" in layout
    notice = (ROOT / "frontend" / "src" / "lib" / "components" / "UpdateNotice.svelte").read_text(encoding="utf-8")
    assert "location.reload()" in notice and notice.count("location.reload") == 1   # 버튼 핸들러 1곳뿐
