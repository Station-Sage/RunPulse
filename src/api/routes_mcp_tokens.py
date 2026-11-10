"""`/api/v1/settings/mcp-tokens` — 원격 MCP 토큰 목록/발급/폐기(세션 사용자 한정). design MCP-REMOTE R8."""
from __future__ import annotations

from flask import Response, request

from src.mcp_remote import audit, token_index as ti
from src.utils.user_context import get_current_user_id

from . import api_bp, api_error, api_ok
from .validation import FieldError, int_field, json_object

MAX_LABEL = 40


def _no_store(resp):
    body, status = resp
    body.headers["Cache-Control"] = "no-store"
    return body, status


def _enabled() -> bool:
    from src.mcp_remote.http import enabled

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


def _parse_issue() -> tuple[tuple[str, int] | None, object]:
    """발급 본문 → ((label, days), err). D-19·D-20·D-21: 조용히 보정하지 않고 400."""
    body, err = json_object()
    if err:
        return None, err
    raw = body.get("label")
    if raw is not None and not isinstance(raw, str):
        return None, api_error("LABEL_INVALID", "이름은 글자로 입력해 주세요", 400)
    label = (raw or "").strip()
    if not label:
        return None, api_error("LABEL_REQUIRED", "이름을 입력해 주세요", 400)
    if len(label) > MAX_LABEL:
        return None, api_error("LABEL_TOO_LONG", f"이름은 {MAX_LABEL}자 이하로 입력해 주세요", 400)
    days = body.get("days")
    if days is None:
        return (label, ti.DEFAULT_DAYS), None
    try:
        days = int_field(1, 365).parse(days)
    except FieldError:
        return None, api_error("BAD_DAYS", "유효 기간은 1~365일 사이 정수예요", 400)
    return (label, days), None


@api_bp.post("/settings/mcp-tokens")
def post_mcp_token():
    uid = get_current_user_id()
    parsed, err = _parse_issue()
    if err:
        return _no_store(err)
    label, days = parsed
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
