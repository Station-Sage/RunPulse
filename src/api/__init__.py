"""Phase 7 `/api/v1/` 블루프린트 — SvelteKit(v2)용 JSON API.

기존 v1 뷰의 `{ok, error}` ad-hoc 포맷과 달리, `05-tech-architecture.md` §3.3이 정한
`{data, meta?}` / `{error: {code, message}}` 포맷을 쓴다 — SvelteKit `apiFetch()`
클라이언트가 `res.json().data`를 그대로 destructure하기 때문(같은 문서 §4.2).

새 비즈니스 로직 없음 — routes_*.py는 src/services/의 기존 함수를 그대로 호출한다.

설계 문서: v0.3/data/phase-7-ui-renewal/05-tech-architecture.md §3
"""
from __future__ import annotations

from flask import Blueprint, jsonify

api_bp = Blueprint("api", __name__, url_prefix="/api/v1")


def api_ok(data, status: int = 200, meta: dict | None = None):
    body = {"data": data}
    if meta:
        body["meta"] = meta
    return jsonify(body), status


def api_error(code: str, message: str, status: int = 400):
    return jsonify({"error": {"code": code, "message": message}}), status


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


from . import routes_coach, routes_library, routes_plan, routes_prediction, routes_today  # noqa: E402,F401
