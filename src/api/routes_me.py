"""사용자 설정 API — /api/v1/me/preferences (ADR-023). 저장소만 제공하며 `/` 분기 연결은 G0 작업."""
from __future__ import annotations

import sqlite3

from flask import request

from src.services import user_settings_service as svc
from src.utils.config import load_config
from src.web.helpers import db_path

from . import api_bp, api_error, api_ok


def _open():
    dpath = db_path()
    return sqlite3.connect(str(dpath)) if dpath.exists() else None


def _payload(conn) -> dict:
    config = load_config()
    return {
        "ui_default": svc.resolve_ui_default(conn, config),
        "ui_default_global": svc.global_ui_default(config),
        "onboarding": svc.get_setting(conn, "onboarding", "pending"),
        "onboarding_step": svc.get_setting(conn, "onboarding_step", 0),
    }


@api_bp.get("/me/preferences")
def get_preferences():
    conn = _open()
    if conn is None:
        return api_error("NOT_FOUND", "running.db 없음", 503)
    try:
        return api_ok(_payload(conn))
    finally:
        conn.close()


@api_bp.patch("/me/preferences")
def patch_preferences():
    body = request.get_json(silent=True)
    keys = [k for k in svc.ALLOWED if isinstance(body, dict) and k in body]
    if not keys:
        return api_error("INVALID_PARAM", f"{', '.join(svc.ALLOWED)} 중 하나가 필요해요", 400)
    conn = _open()
    if conn is None:
        return api_error("NOT_FOUND", "running.db 없음", 503)
    try:
        for k in keys:
            svc.set_setting(conn, k, body[k])
        return api_ok(_payload(conn))
    except ValueError as e:
        return api_error("INVALID_PARAM", str(e), 400)
    finally:
        conn.close()
