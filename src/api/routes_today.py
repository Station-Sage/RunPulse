"""GET /api/v1/today, POST /api/v1/today/checkin — Phase 7a."""
from __future__ import annotations

import sqlite3

from flask import request

from src.services import today_service
from src.web.helpers import db_path

from . import api_bp, api_error, api_ok


@api_bp.get("/today")
def get_today():
    dpath = db_path()
    if not dpath.exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)

    conn = sqlite3.connect(str(dpath))
    try:
        status = today_service.get_today_status(conn)
        briefing = today_service.get_today_briefing(conn)
        recent_activities = today_service.get_recent_activities(conn, limit=3)
        checkin = today_service.get_todays_checkin(conn)
    finally:
        conn.close()

    return api_ok({
        "status": status,
        "briefing": briefing,
        "recent_activities": recent_activities,
        "checkin": checkin,
    })


@api_bp.post("/today/checkin")
def post_today_checkin():
    dpath = db_path()
    if not dpath.exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)

    body = request.get_json(silent=True) or {}
    conn = sqlite3.connect(str(dpath))
    try:
        result = today_service.save_checkin(
            conn,
            fatigue=body.get("fatigue"),
            pain=body.get("pain"),
            note=body.get("note"),
        )
    finally:
        conn.close()

    return api_ok({**result, "saved_at": result["created_at"]})
