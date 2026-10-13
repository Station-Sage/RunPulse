"""Phase 7 `/api/v1/` 블루프린트 — SvelteKit(v2)용 JSON API.

기존 v1 뷰의 `{ok, error}` ad-hoc 포맷과 달리, `05-tech-architecture.md` §3.3이 정한
`{data, meta?}` / `{error: {code, message}}` 포맷을 쓴다 — SvelteKit `apiFetch()`
클라이언트가 `res.json().data`를 그대로 destructure하기 때문(같은 문서 §4.2).

새 비즈니스 로직 없음 — routes_*.py는 src/services/의 기존 함수를 그대로 호출한다.

설계 문서: v0.3/data/phase-7-ui-renewal/05-tech-architecture.md §3
"""
from __future__ import annotations

import logging

from flask import Blueprint, jsonify, request
from werkzeug.exceptions import HTTPException

from src.utils.user_context import InvalidUserId

logger = logging.getLogger(__name__)

api_bp = Blueprint("api", __name__, url_prefix="/api/v1")


def api_ok(data, status: int = 200, meta: dict | None = None):
    body = {"data": data}
    if meta:
        body["meta"] = meta
    return jsonify(body), status


def api_ok_cacheable(data, status: int = 200, meta: dict | None = None):
    """api_ok와 같은 포맷이지만 ETag(응답 본문 해시)를 붙여 조건부 GET을 지원한다.

    활동 상세·스트림처럼 동기화 후엔 거의 안 바뀌는 무거운 페이로드용 — 사용자가 늘어날수록
    같은 활동을 반복 조회할 때마다 매번 전체를 다시 보내는 게 낭비라 추가함. 브라우저가
    If-None-Match로 재검증하면 내용이 같을 때 본문 없이 304만 응답(Werkzeug 표준 동작).
    내용이 바뀌면(재동기화 등) 해시도 달라져 자동으로 새로 내려감 — max-age 캐시처럼 기간을
    임의로 정할 필요가 없다.
    """
    body = {"data": data}
    if meta:
        body["meta"] = meta
    response = jsonify(body)
    response.status_code = status
    response.add_etag()
    return response.make_conditional(request)


def api_error(code: str, message: str, status: int = 400, details: dict | None = None):
    err = {"code": code, "message": message}
    if details is not None:
        err["details"] = details
    return jsonify({"error": err}), status


def register_envelope_handlers(bp: Blueprint) -> None:
    """블루프린트의 모든 오류를 `{error:{code,message}}` 봉투로 내보내는 공용 핸들러 등록 (SRV 2.3).

    - `HTTPException`(뷰 안의 400/404/413/415 등) → 같은 상태코드의 봉투. 응답 헤더(`Allow` 등)는 유지한다.
    - 그 밖의 예외 → 서버 로그에 스택을 남기고 `INTERNAL` 500 봉투(메시지에 예외 내용을 싣지 않음).
    입력 검증이 빠진 라우트가 남아도 HTML 500 이 나가지 않게 하는 안전망이며 검증을 대체하지 않는다.

    `api_bp` 와 `/api/context-episodes` 블루프린트(NEW-40)가 같은 함수로 등록한다(복제 금지).
    제약(Flask 동작, S3 1단계에서 확인): 블루프린트 핸들러는 '라우트가 매칭된 요청'에만 적용된다.
    라우팅 단계에서 나는 404(없는 URL)·405(허용 안 되는 메서드)는 `url_rule` 이 없어 이 핸들러 밖이며
    기본 HTML 로 나간다. 뷰 안에서 `abort()`·예외로 난 오류는 모두 봉투가 된다.
    """

    @bp.errorhandler(HTTPException)
    def _http_error(exc: HTTPException):
        status = exc.code or 500
        code = _HTTP_ERROR_CODES.get(status) or exc.name.upper().replace(" ", "_")
        resp, _ = api_error(code, exc.description or exc.name, status)
        for key, value in exc.get_headers():
            if key.lower() not in ("content-type", "content-length"):
                resp.headers[key] = value
        return resp, status

    @bp.errorhandler(InvalidUserId)
    def _invalid_user(exc: InvalidUserId):
        # get_db_path 등 깊은 곳에서 올라온 uid 규칙 위반(V1-20 이중 방어) — 500 으로 새지 않게 403 봉투
        logging.getLogger("runpulse.security").warning("[api] uid 규칙 위반 %s (path=%s)", exc.masked, request.path)
        return api_error("FORBIDDEN_USER", "허용되지 않는 사용자 식별자입니다.", 403)

    @bp.errorhandler(Exception)
    def _unhandled_error(exc: Exception):
        logger.exception("[api] 처리되지 않은 예외 %s %s", request.method, request.path)
        return api_error("INTERNAL", "서버 내부 오류가 발생했습니다.", 500)


_HTTP_ERROR_CODES = {
    400: "BAD_REQUEST",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    413: "TOO_LARGE",
    415: "UNSUPPORTED_MEDIA_TYPE",
    500: "INTERNAL",
}

register_envelope_handlers(api_bp)

_LIVE_TODAY_PREFIXES = ("/api/v1/today", "/api/v1/library/metrics")


@api_bp.before_request
def _refresh_today_metrics():
    """오늘 화면·메트릭 브라우저 조회 전에 오늘 행이 오래됐으면 현 시각 기준으로 다시 계산."""
    from flask import request

    if request.method != "GET" or not request.path.startswith(_LIVE_TODAY_PREFIXES):
        return None
    import sqlite3

    from src.metrics.today_refresh import refresh_today_if_stale
    from src.utils.user_context import db_path

    dpath = db_path()
    if not dpath.exists():
        return None
    conn = sqlite3.connect(str(dpath), timeout=30)
    try:
        refresh_today_if_stale(conn)
    finally:
        conn.close()
    return None


from . import routes_coach, routes_data, routes_data_ai, routes_data_calendar, routes_data_export, routes_data_import, routes_library, routes_library_activities, routes_library_export, routes_library_feedback, routes_mcp_tokens, routes_me, routes_plan, routes_plan_adjust, routes_plan_replan, routes_prediction, routes_story, routes_today  # noqa: E402,F401
