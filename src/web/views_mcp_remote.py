"""원격 MCP 엔드포인트 — POST /mcp (Streamable HTTP, JSON 단발·무상태, Bearer 토큰 인증).

세션·쿠키를 쓰지 않고 요청 사용자는 토큰 행의 user_id뿐이다. 설정 mcp_remote.enabled=false면 404.
설계: v0.3/data/phase-7-ui-renewal/ux-review-2026-09/DESIGN-MCP-REMOTE.md §2
"""
from __future__ import annotations

import json
import logging
import time
from urllib.parse import urlparse

from flask import Blueprint, Response, request

from src.db_setup import get_db_path
from src.mcp_remote import audit, token_index
from src.mcp_remote.policy import REMOTE_TOOLS
from src.mcp_remote.protocol import SUPPORTED_VERSIONS, handle_message
from src.mcp_remote.safe_conn import connect_readonly
from src.utils import rate_window
from src.utils.config import load_config

log = logging.getLogger(__name__)
mcp_remote_bp = Blueprint("mcp_remote", __name__)

MAX_BODY = 64 * 1024
CALL_LIMITS = ((120, 600), (1500, 86400))
FAIL_LIMIT = (20, 600)


def enabled() -> bool:
    """킬 스위치 — 루트 설정(세션 비의존)의 mcp_remote.enabled."""
    return bool((load_config(user_id="default").get("mcp_remote") or {}).get("enabled", False))


def _ip() -> str:
    return (request.headers.get("CF-Connecting-IP") or request.remote_addr or "?").strip()


def _resp(status: int, body: dict | None = None, headers: dict | None = None) -> Response:
    data = "" if body is None else json.dumps(body, ensure_ascii=False)
    r = Response(data, status=status, mimetype="application/json")
    r.headers["Cache-Control"] = "no-store"
    for k, v in (headers or {}).items():
        r.headers[k] = v
    return r


def _err(status: int, msg: str, headers: dict | None = None) -> Response:
    return _resp(status, {"error": msg}, headers)


def _bearer() -> str:
    h = request.headers.get("Authorization", "")
    return h[7:].strip() if h[:7].lower() == "bearer " else ""


def _origin_ok() -> bool:
    origin = request.headers.get("Origin")
    return not origin or urlparse(origin).netloc == request.host


def _auth_fail(method: str | None, ip: str) -> Response:
    rate_window.hit(f"mcpfail:{ip}", *FAIL_LIMIT)
    audit.record(token_id=None, user_id=None, method=method, tool=None, args=None,
                 status="auth_fail", ip=ip)
    return _err(401, "unauthorized", {"WWW-Authenticate": "Bearer"})


@mcp_remote_bp.route("/mcp", methods=["POST", "GET", "DELETE"], strict_slashes=False)
def mcp_endpoint() -> Response:
    if not enabled():
        return Response("Not Found", status=404, mimetype="text/plain")
    if request.method != "POST":
        return _err(405, "method not allowed", {"Allow": "POST"})
    ip = _ip()
    if rate_window.count(f"mcpfail:{ip}", FAIL_LIMIT[1]) >= FAIL_LIMIT[0]:
        return _err(429, "too many requests", {"Retry-After": "600"})
    if not _origin_ok():
        return _err(403, "forbidden")
    found = token_index.lookup(_bearer())
    if not found:
        return _auth_fail(None, ip)
    tid, uid = found["token_id"], found["user_id"]
    if (request.content_length or 0) > MAX_BODY:
        return _err(413, "payload too large")
    ver = request.headers.get("MCP-Protocol-Version")
    if ver and ver not in SUPPORTED_VERSIONS:
        return _err(400, "unsupported protocol version")
    msg = request.get_json(silent=True)
    if not isinstance(msg, dict):
        audit.record(token_id=tid, user_id=uid, method=None, tool=None, args=None,
                     status="bad_request", ip=ip)
        return _err(400, "invalid request")
    method = msg.get("method")
    params = msg.get("params") if isinstance(msg.get("params"), dict) else {}
    tool = params.get("name") if method == "tools/call" else None
    if method == "tools/call":
        for n, w in CALL_LIMITS:
            if rate_window.count(f"mcpcall:{tid}:{w}", w) >= n:
                audit.record(token_id=tid, user_id=uid, method=method, tool=tool, args=None,
                             status="rate_limited", ip=ip)
                return _err(429, "rate limited", {"Retry-After": str(min(w, 600))})
        for n, w in CALL_LIMITS:
            rate_window.hit(f"mcpcall:{tid}:{w}", n, w)
    token_index.touch(tid, (request.headers.get("User-Agent") or "")[:60])

    t0 = time.monotonic()
    out = handle_message(msg, lambda: connect_readonly(get_db_path(uid, create=False)),
                         allowed=REMOTE_TOOLS, generic_errors=True)
    ms = int((time.monotonic() - t0) * 1000)
    if out is None:
        if method != "ping":
            audit.record(token_id=tid, user_id=uid, method=method, tool=None, args=None,
                         status="ok", latency_ms=ms, ip=ip)
        return _resp(202)
    body = json.dumps(out, ensure_ascii=False)
    if method != "ping":
        res = out.get("result") or {}
        status = "ok"
        if "error" in out:
            status = "bad_request"
        elif res.get("isError"):
            status = "tool_error"
        audit.record(token_id=tid, user_id=uid, method=method, tool=tool,
                     args=params.get("arguments") if tool else None, status=status,
                     latency_ms=ms, resp_bytes=len(body.encode()), ip=ip)
    return _resp(200, out)
