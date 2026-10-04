"""GET /api/v1/library/activities/facets · /summary — 목록 칩·월/주 요약 (UX 리뷰 20 §7-2 ⑤, B-3)."""
from __future__ import annotations

import sqlite3

from flask import request

from src.services import activity_list_filters, activity_list_summary
from src.web.helpers import db_path

from . import api_bp, api_error, api_ok


def _run(fn):
    dpath = db_path()
    if not dpath.exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)
    try:
        filters = activity_list_filters.parse_args(request.args)
    except ValueError as e:
        return api_error("INVALID_PARAM", f"잘못된 파라미터: {e}", 400)
    conn = sqlite3.connect(str(dpath))
    try:
        return api_ok(fn(conn, filters))
    finally:
        conn.close()


@api_bp.get("/library/activities/facets")
def get_library_activity_facets():
    return _run(activity_list_summary.get_facets)


@api_bp.get("/library/activities/summary")
def get_library_activity_summary():
    return _run(activity_list_summary.get_summary)
