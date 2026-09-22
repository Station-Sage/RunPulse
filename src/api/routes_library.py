"""GET /api/v1/library/activities(+:id, +:id/streams) — Phase 7a."""
from __future__ import annotations

import sqlite3

from flask import request

from src.services import activity_service
from src.web.helpers import db_path

from . import api_bp, api_error, api_ok


@api_bp.get("/library/activities")
def get_library_activities():
    dpath = db_path()
    if not dpath.exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)

    filters: dict = {}
    if request.args.get("sport"):
        filters["activity_type"] = request.args["sport"]
    if request.args.get("from"):
        filters["date_from"] = request.args["from"]
    if request.args.get("to"):
        filters["date_to"] = request.args["to"]

    try:
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 20))
    except ValueError:
        return api_error("INVALID_PARAM", "page/per_page는 정수여야 합니다.", 400)

    conn = sqlite3.connect(str(dpath))
    try:
        result = activity_service.get_activity_list(
            conn, filters=filters, page=page, per_page=per_page,
        )
    finally:
        conn.close()

    return api_ok(
        {
            "activities": result["activities"],
            "total": result["total"],
            "has_more": result["page"] < result["total_pages"],
        },
        meta={"page": result["page"], "per_page": result["per_page"]},
    )


@api_bp.get("/library/activities/<int:activity_id>")
def get_library_activity_detail(activity_id: int):
    dpath = db_path()
    if not dpath.exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)

    conn = sqlite3.connect(str(dpath))
    try:
        detail = activity_service.get_activity_detail(conn, activity_id)
    finally:
        conn.close()

    if not detail["core"]:
        return api_error("NOT_FOUND", f"활동을 찾을 수 없습니다: {activity_id}", 404)

    return api_ok({"activity": detail})


@api_bp.get("/library/activities/<int:activity_id>/streams")
def get_library_activity_streams(activity_id: int):
    dpath = db_path()
    if not dpath.exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)

    conn = sqlite3.connect(str(dpath))
    try:
        streams = activity_service.get_activity_streams(
            conn, activity_id, source=request.args.get("source"),
        )
    finally:
        conn.close()

    return api_ok({"streams": streams})
