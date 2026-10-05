"""활동 원본 링크·GPX 내보내기 — /api/v1/library/activities/<id>/source-links · export.gpx (ADR-022)."""
from __future__ import annotations

import sqlite3

from flask import Response

from src.services import activity_gpx, activity_source_links
from src.web.helpers import db_path

from . import api_bp, api_error, api_ok


def _conn_for(activity_id: int):
    dpath = db_path()
    if not dpath.exists():
        return None, api_error("NOT_FOUND", "running.db 없음", 503)
    conn = sqlite3.connect(str(dpath))
    if conn.execute("SELECT 1 FROM activity_summaries WHERE id=?", (activity_id,)).fetchone() is None:
        conn.close()
        return None, api_error("NOT_FOUND", "활동 없음", 404)
    return conn, None


@api_bp.get("/library/activities/<int:activity_id>/source-links")
def get_activity_source_links(activity_id: int):
    conn, err = _conn_for(activity_id)
    if err:
        return err
    try:
        return api_ok({"links": activity_source_links.source_links(conn, activity_id)})
    finally:
        conn.close()


@api_bp.get("/library/activities/<int:activity_id>/export.gpx")
def get_activity_gpx(activity_id: int):
    conn, err = _conn_for(activity_id)
    if err:
        return err
    try:
        body, filename = activity_gpx.build_gpx(conn, activity_id)
    except activity_gpx.NoGpsError:
        return api_error("NO_GPS", "위치 기록이 없는 활동이에요", 404)
    finally:
        conn.close()
    return Response(body, mimetype="application/gpx+xml",
                    headers={"Content-Disposition": f"attachment; filename={filename}"})
