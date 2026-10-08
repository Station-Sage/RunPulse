"""AI 설정 라우트 — GET/PATCH /data/settings/ai, POST /data/settings/ai/test (F-DATA-12)."""
from __future__ import annotations

import sqlite3

from flask import request

from src.ai.provider_common import LLM_PROVIDERS
from src.services import ai_settings_service as svc
from src.utils.config import load_config
from src.web.helpers import db_path, get_current_user_id

from . import api_bp, api_error, api_ok


def _open():
    dpath = db_path()
    return sqlite3.connect(str(dpath)) if dpath.exists() else None


@api_bp.get("/data/settings/ai")
def get_ai_settings():
    conn = _open()
    if conn is None:
        return api_error("NOT_FOUND", "running.db 없음", 503)
    try:
        return api_ok(svc.build_view(conn, load_config(user_id=get_current_user_id())))
    finally:
        conn.close()


@api_bp.patch("/data/settings/ai")
def patch_ai_settings():
    changes, err = svc.validate_patch(request.get_json(silent=True) or {})
    if err:
        return api_error("INVALID_PARAM", err, 400)
    conn = _open()
    if conn is None:
        return api_error("NOT_FOUND", "running.db 없음", 503)
    uid = get_current_user_id()
    try:
        config = load_config(user_id=uid)
        svc.apply_patch(conn, config, uid, changes)
        return api_ok(svc.build_view(conn, config))
    finally:
        conn.close()


@api_bp.post("/data/settings/ai/test")
def test_ai_connection():
    provider = (request.get_json(silent=True) or {}).get("provider")
    if provider not in LLM_PROVIDERS:
        return api_error("INVALID_PARAM", f"provider는 {', '.join(LLM_PROVIDERS)} 중 하나예요", 400)
    return api_ok(svc.test_connection(provider, load_config(user_id=get_current_user_id())))
