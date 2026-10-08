"""`/api/v1/settings/mcp-tokens` — 원격 MCP 토큰 목록/발급/폐기(세션 사용자 한정). design MCP-REMOTE R8."""
from __future__ import annotations

from flask import Response, request

from src.mcp_remote import audit, token_index as ti
from src.web.helpers import get_current_user_id

from . import api_bp, api_error, api_ok

MAX_LABEL = 40


def _no_store(resp):
    body, status = resp
    body.headers["Cache-Control"] = "no-store"
    return body, status


def _enabled() -> bool:
    from src.web.views_mcp_remote import enabled

    return enabled()


def _audit(uid: str, token_id: str | None, method: str) -> None:
    audit.record(token_id=token_id, user_id=uid, method=method, tool=None, args=None,
                 status="ok", ip=request.remote_addr or "")


@api_bp.get("/settings/mcp-tokens")
def get_mcp_tokens():
    uid = get_current_user_id()
    return _no_store(api_ok({"enabled": _enabled(), "max_active": ti.MAX_ACTIVE_PER_USER,
                             "default_days": ti.DEFAULT_DAYS,
                             "tokens": ti.list_tokens(uid)}))


@api_bp.post("/settings/mcp-tokens")
def post_mcp_token():
    uid = get_current_user_id()
    body = request.get_json(silent=True) or {}
    label = str(body.get("label") or "").strip()[:MAX_LABEL]
    if not label:
        return _no_store(api_error("LABEL_REQUIRED", "이름을 입력해 주세요", 400))
    try:
        days = int(body.get("days") or ti.DEFAULT_DAYS)
    except (TypeError, ValueError):
        return _no_store(api_error("BAD_DAYS", "유효 기간이 올바르지 않아요", 400))
    try:
        token, meta = ti.issue(uid, label, days)
    except ti.TokenError as e:
        return _no_store(api_error("TOKEN_LIMIT", str(e), 409))
    _audit(uid, meta["token_id"], "token_issue")
    return _no_store(api_ok({**meta, "token": token}, 201))


@api_bp.delete("/settings/mcp-tokens/<token_id>")
def delete_mcp_token(token_id: str):
    uid = get_current_user_id()
    if not ti.revoke(token_id, uid):
        return _no_store(api_error("NOT_FOUND", "대상 토큰이 없어요", 404))
    _audit(uid, token_id, "token_revoke")
    return Response(status=204, headers={"Cache-Control": "no-store"})
