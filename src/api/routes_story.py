"""GET /api/v1/library/story/<period> — Phase 7 Story endpoint."""
from __future__ import annotations

import sqlite3

from flask import request

from src.services import story_service
from src.utils.config import load_config
from src.web.helpers import db_path, get_current_user_id

from . import api_bp, api_error, api_ok


@api_bp.get("/library/story/<period>")
def get_story(period: str):
    """훈련 이야기 조회 — 월/주/블록 단위.

    period: 2026-09 | 2026-W39 | b-<planId>-<phase>
    """
    dpath = db_path()
    if not dpath.exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)

    try:
        config = load_config(user_id=get_current_user_id())
        conn = sqlite3.connect(str(dpath))
        try:
            result = story_service.get_story(conn, period, config=config)
        finally:
            conn.close()
        return api_ok(result)

    except ValueError as e:
        return api_error("INVALID_PERIOD", str(e), 400)
    except Exception as e:
        return api_error("SERVER_ERROR", str(e), 500)
