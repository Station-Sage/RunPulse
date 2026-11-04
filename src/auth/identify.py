"""AUTH_MODE=registry 의 before_request 신원 해석 — g.auth_state ∈ anonymous|pending|active.

비공개 경로는 검증된 CF JWT 가 필수이며 세션만으로는 통과하지 못한다(F1·F2). 공개 경로는 세션으로 상태만 표시한다.
pending 은 session["user_id"] 를 갖지 않는다(데이터 접근 불가). 레거시 동작은 src/web/auth_cf.py 가 그대로 담당한다.
"""
from __future__ import annotations

import logging
import os

from flask import Flask, Response, g, jsonify, request, session

from src.utils.user_context import InvalidUserId

from . import cf_jwt, registry
from .public_paths import is_public, pending_allowed

log = logging.getLogger(__name__)
_IS_PRODUCTION = os.environ.get("APP_ENV", "development").lower() == "production"


def _err(code: str, message: str, status: int) -> Response:
    if request.path.startswith("/api/"):
        resp = jsonify({"ok": False, "error": {"code": code, "message": message}})
    else:
        resp = Response(message, mimetype="text/plain")
    resp.status_code = status
    return resp


def _token() -> str:
    return request.headers.get(cf_jwt.JWT_HEADER, "") or request.cookies.get(cf_jwt.JWT_COOKIE, "")


def _idp_type(claims: dict) -> str | None:
    idp = claims.get("idp")
    return idp.get("type") if isinstance(idp, dict) else None


def _set_state(state: str, uid: str | None = None, email: str | None = None) -> None:
    g.auth_state, g.auth_uid, g.auth_email = state, uid, email


def _service_token_uid() -> str | None:
    """CF 서비스 토큰 바이패스(CF 미경유 내부 호출용) — 루트 config 의 자격증명과 일치할 때만."""
    from src.web.auth_cf import _load_svc_token

    sid, secret, user = _load_svc_token()
    if sid and request.headers.get("CF-Access-Client-Id") == sid and request.headers.get("CF-Access-Client-Secret") == secret:
        try:
            from src.utils.user_context import validate_uid
            validate_uid(user)
            return user
        except InvalidUserId:
            return None
    return None


def _from_session() -> None:
    if session.get("user_id") and session.get("auth_sub"):
        _set_state("active", session["user_id"], session.get("auth_email"))
    elif session.get("pending_sub"):
        _set_state("pending", None, session.get("auth_email"))
    else:
        _set_state("anonymous")


def _resolve(claims: dict) -> Response | None:
    """검증된 claims → 계정 조회/연결/생성. 세션을 갱신하고 g 상태를 정한다."""
    sub, email = str(claims["sub"]), registry.normalize_email(claims.get("email", ""))
    if session.get("auth_sub") not in (None, sub) or session.get("pending_sub") not in (None, sub):
        session.clear()  # 다른 신원으로 바뀌면 이전 세션을 승계하지 않는다
    conn = registry.connect()
    try:
        acct = registry.account_by_identity(conn, sub)
        if acct is None:
            if not email:
                return _err("FORBIDDEN_USER", "이메일이 확인되지 않는 로그인입니다.", 403)
            acct = registry.account_by_email(conn, email)
            try:
                if acct is None:
                    acct = registry.create_pending(conn, email)
                    registry.record_event(conn, "signup_pending", acct["uid"])
                registry.link_identity(conn, acct["uid"], sub, email, _idp_type(claims))
            except InvalidUserId:
                return _err("FORBIDDEN_USER", "허용되지 않는 사용자 식별자입니다.", 403)
        else:
            registry.link_identity(conn, acct["uid"], sub, email)
    finally:
        conn.close()
    status = acct["status"]
    if status == "disabled":
        session.clear()
        _set_state("anonymous")
        return _err("ACCOUNT_DISABLED", "사용이 중지된 계정입니다.", 403)
    session.permanent = True
    session["auth_sub"], session["auth_email"] = sub, email
    if status == "active":
        session.pop("pending_sub", None)
        session["user_id"] = acct["uid"]
        _set_state("active", acct["uid"], email)
    else:
        session.pop("user_id", None)
        session["pending_sub"] = sub
        _set_state("pending", None, email)
    return None


def _identify() -> Response | None:
    method, path = request.method, request.path
    public = is_public(method, path)
    token = _token()
    if not token:
        if public:
            _from_session()
            return None
        svc_uid = _service_token_uid()
        if svc_uid:
            session["user_id"], session["auth_sub"] = svc_uid, "service"
            _set_state("active", svc_uid, svc_uid)
            return None
        if not _IS_PRODUCTION and not os.environ.get("CF_ACCESS_AUD"):
            uid = os.environ.get("DEV_USER_ID", "default")
            session["user_id"], session["auth_sub"] = uid, "dev"
            _set_state("active", uid, uid)
            return None
        _set_state("anonymous")
        return _err("AUTH_REQUIRED", "로그인이 필요합니다.", 401)
    try:
        claims = cf_jwt.verify(token)
    except cf_jwt.CfJwtError as exc:
        log.warning("[auth] CF JWT 검증 실패 (%s, path=%s)", exc, path)
        session.clear()
        _set_state("anonymous")
        if public:
            return None
        return _err("AUTH_REQUIRED", "로그인이 필요합니다.", 401)
    denied = _resolve(claims)
    if denied is not None:
        return denied
    if g.auth_state == "pending" and not public and not pending_allowed(method, path):
        return _err("AUTH_PENDING", "가입 승인이 필요합니다.", 403)
    return None


def init_registry_auth(app: Flask) -> None:
    app.before_request(_identify)
