"""활동 피드백(RPE·통증·메모) GET/PUT/DELETE — /api/v1/library/activities/<id>/feedback (ADR-022)."""
from __future__ import annotations

import sqlite3

from flask import request

from src.services import activity_feedback_service as svc
from src.web.helpers import db_path

from . import api_bp, api_error, api_ok


def _open():
    dpath = db_path()
    return sqlite3.connect(str(dpath)) if dpath.exists() else None


def _exists(conn, activity_id: int) -> bool:
    return conn.execute("SELECT 1 FROM activity_summaries WHERE id=?", (activity_id,)).fetchone() is not None


@api_bp.get("/library/activities/<int:activity_id>/feedback")
def get_activity_feedback(activity_id: int):
    conn = _open()
    if conn is None:
        return api_error("NOT_FOUND", "running.db 없음", 503)
    try:
        if not _exists(conn, activity_id):
            return api_error("NOT_FOUND", "활동 없음", 404)
        return api_ok({"feedback": svc.get_feedback(conn, activity_id)})
    finally:
        conn.close()


@api_bp.put("/library/activities/<int:activity_id>/feedback")
def put_activity_feedback(activity_id: int):
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return api_error("INVALID_PARAM", "JSON 객체가 필요해요", 400)
    conn = _open()
    if conn is None:
        return api_error("NOT_FOUND", "running.db 없음", 503)
    try:
        return api_ok({"feedback": svc.put_feedback(conn, activity_id, body)})
    except LookupError:
        return api_error("NOT_FOUND", "활동 없음", 404)
    except svc.FeedbackError as e:
        return api_error(e.code, str(e), 400)
    finally:
        conn.close()


@api_bp.delete("/library/activities/<int:activity_id>/feedback")
def delete_activity_feedback(activity_id: int):
    conn = _open()
    if conn is None:
        return api_error("NOT_FOUND", "running.db 없음", 503)
    try:
        svc.delete_feedback(conn, activity_id)
        return "", 204
    finally:
        conn.close()
