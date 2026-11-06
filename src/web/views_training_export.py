"""훈련 계획 ICS 다운로드 라우트 (v1 push-garmin/push-caldav 는 S4-70 에서 제거).

views_training_crud.py에서 분리 (2026-03-29).
"""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from flask import Blueprint, Response, request

from src.utils.user_context import db_path

training_export_bp = Blueprint("training_export", __name__)


@training_export_bp.route("/training/export.ics")
def training_export_ics():
    """주간 훈련 계획을 iCal 형식으로 내보내기."""
    dbp = db_path()
    if not dbp or not dbp.exists():
        return Response("No data", status=404)

    week_offset = request.args.get("week", 0, type=int)
    from src.services.calendar_feed_service import build_ics

    today = date.today()
    start = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)
    try:
        conn = sqlite3.connect(str(dbp))
        try:
            body = build_ics(conn, start.isoformat(), (start + timedelta(days=6)).isoformat())
        finally:
            conn.close()
    except Exception:
        body = "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//RunPulse//Training Plan//KO\r\nEND:VCALENDAR\r\n"

    return Response(
        body,
        mimetype="text/calendar",
        headers={"Content-Disposition": "attachment; filename=runpulse-training.ics"},
    )
