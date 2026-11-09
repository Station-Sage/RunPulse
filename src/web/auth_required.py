"""인증 필요(401) 응답 — `/api/` 는 JSON 봉투, 그 외(화면 요청)는 로그인 안내 HTML (E-03).

이전에는 화면 요청에도 text/plain 한 줄만 보여 사용자가 무엇을 해야 할지 알 수 없었다.
- legacy(CF Access) 모드: Cloudflare 가 로그인을 맡으므로 "다시 시도"는 같은 주소를 다시 연다.
- registry 모드: `/auth/start?next=` 로 로그인을 시작한다(`next` 는 safe_next 규칙으로 정규화).
"""
from __future__ import annotations

from html import escape
from urllib.parse import quote

from flask import Response, jsonify, request

_PAGE = """<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex"><title>로그인이 필요해요 - RunPulse</title></head>
<body style="margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;\
background:#0f172a;color:#e2e8f0;font-family:system-ui,sans-serif">
<main style="max-width:22rem;padding:1.5rem;text-align:center">
<h1 style="font-size:1.125rem;margin:0 0 .5rem">로그인이 필요해요</h1>
<p style="font-size:.875rem;color:#cbd5e1;margin:0 0 1.25rem">{message}</p>
<a href="{href}" style="display:inline-block;min-height:2.75rem;line-height:2.75rem;padding:0 1rem;\
border-radius:.5rem;background:#38bdf8;color:#0f172a;text-decoration:none;font-weight:600">{label}</a>
</main></body></html>"""


def login_target(path: str, query: str, registry_mode: bool) -> tuple[str, str]:
    """(href, 라벨). registry 는 로그인 시작 경로, legacy 는 같은 주소 다시 열기."""
    if registry_mode:
        from src.auth.public_paths import safe_next
        return f"/auth/start?next={quote(safe_next(path), safe='/')}", "다시 로그인"
    target = path + (f"?{query}" if query else "")
    # 같은 출처 경로만 — `//host` 형태는 루트로 바꾼다(오픈 리다이렉트 방지).
    if not target.startswith("/") or target.startswith("//"):
        target = "/"
    return target, "다시 시도"


def auth_required_response(code: str, message: str, *, registry_mode: bool, status: int = 401) -> Response:
    """`/api/` 는 `{ok:false,error:{code,message}}`, 그 외는 로그인 안내 HTML. 캐시 금지."""
    if request.path.startswith("/api/"):
        resp = jsonify({"ok": False, "error": {"code": code, "message": message}})
    else:
        href, label = login_target(request.path, request.query_string.decode("latin-1"), registry_mode)
        body = _PAGE.format(message=escape(message), href=escape(href, quote=True), label=label)
        resp = Response(body, mimetype="text/html")
    resp.status_code = status
    resp.headers["Cache-Control"] = "no-store"
    return resp
