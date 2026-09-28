"""`/api/v1/data/*` — 데이터 관리(동기화 상태 등). 40-v2-unimplemented design §7.3."""
from __future__ import annotations

import sqlite3

from src.services import sync_state_service
from src.utils.config import load_config
from src.web.helpers import db_path, get_current_user_id

from . import api_bp, api_error, api_ok


@api_bp.get("/data/sync-state")
def get_sync_state():
    dpath = db_path()
    if not dpath.exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)
    config = load_config(user_id=get_current_user_id())
    conn = sqlite3.connect(str(dpath))
    try:
        return api_ok(sync_state_service.get_sync_state(conn, config))
    finally:
        conn.close()
