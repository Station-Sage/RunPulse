"""인증 상태 API — GET /api/v1/auth/session (공개 경로, AUTH_MODE=registry 에서 의미 있음)."""
from __future__ import annotations

from flask import g, session

from . import api_bp, api_ok


@api_bp.get("/auth/session")
def get_auth_session():
    """{state: anonymous|pending|active, email}. legacy 모드에서는 훅이 상태를 안 만들므로 세션으로 추정한다."""
    state = getattr(g, "auth_state", None)
    if state is None:
        state = "active" if session.get("user_id") else "anonymous"
    email = getattr(g, "auth_email", None) or session.get("auth_email")
    resp = api_ok({"state": state, "email": email if state != "anonymous" else None})
    resp.headers["Cache-Control"] = "no-store"
    return resp
