"""개발용 사용자 전환 API — GET /api/v1/dev/users, POST /api/v1/dev/switch-user (V1-8, SRV 2.5).

v1 `/switch-user` 의 이관본이다. production(`APP_ENV == "production"`)에서는 두 경로 모두 404 이며
(같은 변경에서 적용 — V1-9), 쓰기(POST)는 앱 전역 Origin 관문과 `parse_body` 검증을 받는다.
"""
from __future__ import annotations

from flask import abort, request, session

from src.services import user_switch_service as svc
from src.utils.user_context import InvalidUserId, get_current_user_id

from . import api_bp, api_error, api_ok
from .validation import parse_body, str_field

_SWITCH_SCHEMA = {"user_id": str_field(254, required=True)}


@api_bp.before_request
def _dev_only():
    if request.path.startswith("/api/v1/dev/") and not svc.dev_switch_enabled():
        abort(404)  # 봉투 NOT_FOUND (register_envelope_handlers)
    return None


@api_bp.get("/dev/users")
def get_dev_users():
    return api_ok({"users": svc.list_users(), "current": get_current_user_id()})


@api_bp.post("/dev/switch-user")
def post_dev_switch_user():
    clean, err = parse_body(_SWITCH_SCHEMA)
    if err:
        return err
    try:
        uid = svc.switch_user(clean["user_id"], session)
    except InvalidUserId:
        return api_error("INVALID_PARAM", "요청 값이 올바르지 않습니다.", 400,
                         {"user_id": "영문·숫자와 . _ % + @ - 만, 1~254자, 맨 앞 '.' 불가"})
    return api_ok({"user_id": uid, "users": svc.list_users()})
