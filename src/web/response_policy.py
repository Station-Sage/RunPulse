"""앱 전역 응답 정책 — 보안 헤더(공통)와 표면별 CSP (E-01, ADR-049).

설계: design-2026-10/patterns/security-headers.md §2.1 (S3 8단계).
`after_request` 1개로 모든 응답에 공통 헤더를 붙이고, 경로로 분류한 표면(surface)에 맞는 CSP 를 붙인다.

- 표면(`classify_surface`): `v2`(`/v2/`) · `api`(`/api/`, `/mcp` — `/api/context-episodes` 포함) · `feed`(`/feeds/`) ·
  `default`(그 밖: 일몰 전 v1 화면, `/trigger-sync` 등, 미정의 경로 404). `v1` 표면은 없다(V1-15).
- 공통 헤더: nosniff · Referrer-Policy · X-Frame-Options DENY · Permissions-Policy. HSTS 는 Cloudflare 에 위임(D4)해 보내지 않는다.
- CSP: `api`/`feed` 는 항상 enforce(`default-src 'none'`). `v2`·`default` 는 `CSP_V2_MODE`(report-only 기본 → enforce, 2주 관찰 후 전환).
  `v2` 만 index.html 인라인 부트스트랩 해시를 `script-src` 에 넣고, `default` 는 넣지 않는다(SEC-12, 엄격).
- 라우트가 이미 붙인 헤더는 덮어쓰지 않는다(`setdefault`) — 기존 Cache-Control·SSE 헤더 보존.
"""
from __future__ import annotations

import logging
import os
import re
from pathlib import Path

from flask import Flask, Response, request

security_log = logging.getLogger("runpulse.security")

CSP_REPORT_PATH = "/api/v1/csp-report"

MODE_REPORT_ONLY = "report-only"
MODE_ENFORCE = "enforce"
_MODES = (MODE_REPORT_ONLY, MODE_ENFORCE)
_DEFAULT_MODE = MODE_REPORT_ONLY

SURFACE_V2 = "v2"
SURFACE_API = "api"
SURFACE_FEED = "feed"
SURFACE_DEFAULT = "default"

HEADER_CSP = "Content-Security-Policy"
HEADER_CSP_REPORT_ONLY = "Content-Security-Policy-Report-Only"

COMMON_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "X-Frame-Options": "DENY",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}

_HASH_RE = re.compile(r"^sha256-[A-Za-z0-9+/]+={0,2}$")


def _under(path: str, prefix: str) -> bool:
    return path == prefix or path.startswith(prefix + "/")


def classify_surface(path: str) -> str:
    """요청 경로 → 표면. `/api/v1` 접두에 기대지 않는다(`/api/context-episodes` 도 api)."""
    if _under(path, "/v2"):
        return SURFACE_V2
    if _under(path, "/api") or _under(path, "/mcp"):
        return SURFACE_API
    if _under(path, "/feeds"):
        return SURFACE_FEED
    return SURFACE_DEFAULT


def csp_v2_mode() -> str:
    """`CSP_V2_MODE` — 알 수 없는 값은 report-only(차단하지 않는 쪽)로 처리하고 경고한다."""
    raw = os.environ.get("CSP_V2_MODE", _DEFAULT_MODE).strip().lower()
    if raw not in _MODES:
        security_log.warning("[csp] CSP_V2_MODE=%r 은 알 수 없는 값 — report-only 로 처리", raw[:20])
        return _DEFAULT_MODE
    return raw


def _document_policy(script_src: str) -> str:
    return "; ".join([
        "default-src 'self'",
        script_src,
        "style-src 'self' 'unsafe-inline'",   # Svelte style 속성·app.html <div style>
        "img-src 'self' data:",
        "connect-src 'self'",
        "base-uri 'self'",
        "form-action 'self'",
        "object-src 'none'",
        "frame-ancestors 'none'",
        f"report-uri {CSP_REPORT_PATH}",
    ])


def build_csp(surface: str, script_hashes: list[str] | tuple[str, ...] = ()) -> str:
    """표면별 CSP 문자열. `script_hashes` 는 `v2` 에서만 쓴다(`default` 는 인라인 해시 미포함 — SEC-12).

    해시 토큰(`sha256-<base64>`)이 아닌 값은 버린다(헤더 주입 방지). 알 수 없는 표면은 ValueError
    (설계의 `str | None` 대신 — 오타가 'CSP 없음'으로 조용히 새지 않게).
    """
    if surface in (SURFACE_API, SURFACE_FEED):
        return "default-src 'none'; frame-ancestors 'none'"
    if surface == SURFACE_V2:
        tokens = "".join(f" '{h}'" for h in script_hashes if _HASH_RE.match(h))
        return _document_policy(f"script-src 'self'{tokens}")
    if surface == SURFACE_DEFAULT:
        return _document_policy("script-src 'self'")
    raise ValueError(f"unknown surface: {surface!r}")


def common_headers() -> dict[str, str]:
    return dict(COMMON_HEADERS)


def csp_header_for(surface: str, mode: str) -> str:
    """이 표면·모드에서 쓸 CSP 헤더 이름. api/feed 는 모드와 무관하게 enforce."""
    if surface in (SURFACE_API, SURFACE_FEED) or mode == MODE_ENFORCE:
        return HEADER_CSP
    return HEADER_CSP_REPORT_ONLY


def default_index_path() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "frontend" / "build" / "index.html"


def apply_policy(resp: Response, path: str, index_path: Path | None = None) -> Response:
    """응답에 공통 헤더 + 표면 CSP 를 붙인다(이미 있는 헤더는 유지)."""
    for k, v in COMMON_HEADERS.items():
        resp.headers.setdefault(k, v)
    surface = classify_surface(path)
    hashes: list[str] = []
    if surface == SURFACE_V2:
        from .spa_static import inline_script_hashes
        hashes = inline_script_hashes(index_path or default_index_path())
    header = csp_header_for(surface, csp_v2_mode())
    # 같은 이름이든 반대 이름이든 라우트가 CSP 를 직접 정했으면 건드리지 않는다
    if HEADER_CSP not in resp.headers and HEADER_CSP_REPORT_ONLY not in resp.headers:
        resp.headers[header] = build_csp(surface, hashes)
    return resp


def init_response_policy(app: Flask) -> None:
    """`after_request` 1개 등록. `request_guard` 초기화 바로 뒤에 호출한다.

    v2 인라인 해시의 원본 index.html 경로는 `app.config["V2_INDEX_HTML"]`(기본 `frontend/build/index.html`).
    """
    @app.after_request
    def _response_policy(resp: Response) -> Response:
        return apply_policy(resp, request.path, app.config.get("V2_INDEX_HTML"))
