"""UI 이벤트 API — /api/v1/me/ui-events (G5 게이트: v2 방문·v1 복귀 기록)."""
from __future__ import annotations

import sqlite3

from flask import request

from src.services import ui_events_service as svc
from src.web.helpers import db_path

from . import api_bp, api_error, api_ok


def _open():
    dpath = db_path()
    return sqlite3.connect(str(dpath)) if dpath.exists() else None


@api_bp.post("/me/ui-events")
def post_ui_event():
    body = request.get_json(silent=True)
    body = body if isinstance(body, dict) else {}
    kind = body.get("kind")
    if kind not in ("v2_visit", "v1_rollback"):
        return api_error("VALIDATION", "kind 는 v2_visit 또는 v1_rollback", 400)
    conn = _open()
    if conn is None:
        return api_error("NOT_FOUND", "running.db 없음", 503)
    try:
        if kind == "v2_visit":
            return api_ok({"recorded": svc.record_visit(conn)})
        try:
            svc.record_rollback(conn, body.get("reason"), body.get("reason_note"))
        except ValueError as e:
            return api_error("VALIDATION", str(e), 400)
        return api_ok({"recorded": True})
    finally:
        conn.close()


@api_bp.get("/me/ui-events/summary")
def get_ui_events_summary():
    try:
        days = max(1, min(90, int(request.args.get("days", 14))))
    except ValueError:
        return api_error("VALIDATION", "days 는 정수", 400)
    conn = _open()
    if conn is None:
        return api_error("NOT_FOUND", "running.db 없음", 503)
    try:
        return api_ok(svc.summarize(conn, days))
    finally:
        conn.close()
