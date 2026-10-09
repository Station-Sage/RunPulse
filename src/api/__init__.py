"""Phase 7 `/api/v1/` 블루프린트 — SvelteKit(v2)용 JSON API.

기존 v1 뷰의 `{ok, error}` ad-hoc 포맷과 달리, `05-tech-architecture.md` §3.3이 정한
`{data, meta?}` / `{error: {code, message}}` 포맷을 쓴다 — SvelteKit `apiFetch()`
클라이언트가 `res.json().data`를 그대로 destructure하기 때문(같은 문서 §4.2).

새 비즈니스 로직 없음 — routes_*.py는 src/services/의 기존 함수를 그대로 호출한다.

설계 문서: v0.3/data/phase-7-ui-renewal/05-tech-architecture.md §3
"""
from __future__ import annotations

from flask import Blueprint, jsonify, request

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


_LIVE_TODAY_PREFIXES = ("/api/v1/today", "/api/v1/library/metrics")


@api_bp.before_request
def _refresh_today_metrics():
    """오늘 화면·메트릭 브라우저 조회 전에 오늘 행이 오래됐으면 현 시각 기준으로 다시 계산."""
    from flask import request

    if request.method != "GET" or not request.path.startswith(_LIVE_TODAY_PREFIXES):
        return None
    import sqlite3

    from src.metrics.today_refresh import refresh_today_if_stale
    from src.web.helpers import db_path

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
