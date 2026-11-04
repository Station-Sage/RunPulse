"""`/auth/start`(CF 로그인 진입)·`/auth/logout` — AUTH_MODE=registry 전용 블루프린트."""
from __future__ import annotations

from flask import Blueprint, redirect, request, session

from .public_paths import safe_next

auth_bp = Blueprint("auth", __name__)
_CF_LOGOUT = "/cdn-cgi/access/logout"


@auth_bp.get("/auth/start")
def start():
    """CF Access 가 보호하는 경로 — 여기에 도달했다면 JWT 검증을 통과했으므로(훅) `next` 로 돌려보낸다."""
    return redirect(safe_next(request.args.get("next")), 303)


@auth_bp.post("/auth/logout")
def logout():
    """앱 세션을 지우고 CF 세션도 종료한다."""
    session.clear()
    return redirect(_CF_LOGOUT, 303)
