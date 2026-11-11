"""인증 상태 API — GET /api/v1/auth/session (공개 경로, AUTH_MODE=registry 에서 의미 있음)."""
from __future__ import annotations

from flask import g, request, session

from . import api_bp, api_ok
from .validation import json_object


@api_bp.get("/auth/session")
def get_auth_session():
    """{mode, state: anonymous|pending|active, email}. legacy 모드에서는 훅이 상태를 안 만들므로 세션으로 추정한다."""
    state = getattr(g, "auth_state", None)
    if state is None:
        state = "active" if session.get("user_id") else "anonymous"
    email = getattr(g, "auth_email", None) or session.get("auth_email")
    from src.auth import auth_mode

    body, status = api_ok({"mode": auth_mode(), "state": state, "email": email if state != "anonymous" else None})
    body.headers["Cache-Control"] = "no-store"
    return body, status


@api_bp.post("/auth/invite")
def post_auth_invite():
    """pending 계정이 초대코드로 활성화(+프로비저닝)된다. 사용 시도는 IP·계정 단위로 제한한다."""
    from src.auth import registry, signup
    from src.utils import rate_window

    from . import api_error

    if getattr(g, "auth_state", None) != "pending" or not getattr(g, "auth_email", None):
        return api_error("NOT_PENDING", "가입 대기 상태가 아닙니다.", 409)
    uid = getattr(g, "auth_email", None)
    ip = request.headers.get("CF-Connecting-IP") or request.remote_addr or "?"
    if not (rate_window.hit(f"invite:ip:{ip}", 10, 600) and rate_window.hit(f"invite:uid:{uid}", 5, 600)):
        return api_error("RATE_LIMITED", "시도가 너무 많습니다. 잠시 후 다시 시도하세요.", 429)
    body, err = json_object()  # D-21
    if err:
        return err
    code = body.get("code")
    conn = registry.connect()
    try:
        signup.activate_pending(conn, uid, code if isinstance(code, str) else None)
        registry.record_event(conn, "signup_activated", uid, signup.signup_mode())
    except signup.SignupError as e:
        registry.record_event(conn, "signup_denied", uid, e.code)
        msgs = {"SIGNUP_CAP": "오늘 가입 가능 인원이 가득 찼습니다. 내일 다시 시도하세요.",
                "INVITE_INVALID": "초대코드가 올바르지 않거나 만료되었습니다.",
                "NOT_ALLOWED": "가입이 허용되지 않은 계정입니다.",
                "PROVISION_FAILED": "계정 준비에 실패했습니다. 잠시 후 다시 시도하세요."}
        return api_error(e.code, msgs.get(e.code, "가입할 수 없습니다."), e.status)
    finally:
        conn.close()
    session.pop("pending_sub", None)
    session["user_id"] = uid
    g.auth_state = "active"
    return api_ok({"state": "active", "email": uid})
