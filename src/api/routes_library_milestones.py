"""GET /api/v1/library/milestones — 마일스톤 전체 이력(최신순, 커서 페이지네이션·종류 필터, ADR-057).

쿼리: type=a,b(선택) · before=YYYY-MM-DD:id(이전 응답의 next_before) · limit=1..100(기본 50).
"""
from __future__ import annotations

import sqlite3

from flask import request

from src.services import milestone_query
from src.utils.user_context import db_path

from . import api_bp, api_error, api_ok


@api_bp.get("/library/milestones")
def get_library_milestones():
    try:
        types = milestone_query.parse_types(request.args.get("type"))
        before = milestone_query.parse_cursor(request.args.get("before"))
        limit = int(request.args.get("limit", 50))
    except ValueError:
        return api_error("INVALID_PARAM", "type·before·limit 형식이 올바르지 않습니다.", 400)
    if not 1 <= limit <= 100:
        return api_error("INVALID_PARAM", "limit은 1~100 범위여야 합니다.", 400)
    dpath = db_path()
    if not dpath.exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)
    conn = sqlite3.connect(str(dpath))
    try:
        return api_ok(milestone_query.list_milestones(conn, types=types, before=before, limit=limit))
    finally:
        conn.close()
