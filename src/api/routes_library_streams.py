"""GET /api/v1/library/activities/:id/streams + 활동 하위 경로의 잘못된 id JSON 봉투 (UX 리뷰 A-20·A-22)."""
from __future__ import annotations

import sqlite3

from flask import request

from src.services import activity_service
from src.utils.user_context import db_path

from . import api_bp, api_error, api_ok_cacheable


@api_bp.get("/library/activities/<int:activity_id>/streams")
def get_library_activity_streams(activity_id: int):
    dpath = db_path()
    if not dpath.exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)

    conn = sqlite3.connect(str(dpath))
    try:
        # 상세·랩·피드백과 같게 없는 활동은 404(이전엔 200 + 빈 배열, A-22)
        if not activity_service.activity_exists(conn, activity_id):
            return api_error("NOT_FOUND", f"활동을 찾을 수 없습니다: {activity_id}", 404)
        streams = activity_service.get_activity_streams(
            conn, activity_id, source=request.args.get("source"),
        )
        meta = activity_service.get_activity_streams_meta(conn, activity_id)
    finally:
        conn.close()

    # 전체 해상도 스트림(가장 무거운 페이로드) — ETag로 조건부 GET.
    return api_ok_cacheable({"streams": streams, **meta})


@api_bp.route(
    "/library/activities/<path:raw>",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
def bad_library_activity_path(raw: str):
    """`<int:id>` 규칙에 안 맞는 하위 경로 — 라우팅 404 가 HTML 로 나가던 것을 JSON 봉투로(A-20).

    정적 규칙(facets·summary)과 `<int:...>` 규칙이 먼저 매칭되므로 여기는 그 밖의 경로만 온다.
    첫 조각이 양의 정수면 '없는 하위 경로'(404), 아니면 '잘못된 id'(400 INVALID_PARAM).
    """
    head = raw.split("/", 1)[0]
    if head.isdigit() and int(head) > 0 and head == str(int(head)):
        return api_error("NOT_FOUND", "없는 경로입니다.", 404)
    return api_error("INVALID_PARAM", "활동 id는 양의 정수여야 합니다.", 400)
