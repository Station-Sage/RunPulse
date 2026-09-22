"""GET/POST /api/v1/coach/threads(+:id, +:id/messages) — Phase 7a Coach MVP."""
from __future__ import annotations

import sqlite3

from flask import request

from src.services import coach_service
from src.utils.config import load_config
from src.web.helpers import db_path, get_current_user_id

from . import api_bp, api_error, api_ok


@api_bp.get("/coach/threads")
def get_coach_threads():
    dpath = db_path()
    if not dpath.exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)

    conn = sqlite3.connect(str(dpath))
    try:
        threads = coach_service.list_threads(conn)
    finally:
        conn.close()

    return api_ok({"threads": threads})


@api_bp.post("/coach/threads")
def post_coach_threads():
    dpath = db_path()
    if not dpath.exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)

    body = request.get_json(silent=True) or {}
    initial_message = body.get("initial_message")
    if not initial_message:
        return api_error("INVALID_PARAM", "initial_message가 필요합니다.", 400)

    config = load_config(user_id=get_current_user_id())
    conn = sqlite3.connect(str(dpath))
    try:
        result = coach_service.create_thread(conn, initial_message, config=config)
    finally:
        conn.close()

    return api_ok(result, status=201)


@api_bp.get("/coach/threads/<int:thread_id>")
def get_coach_thread_detail(thread_id: int):
    dpath = db_path()
    if not dpath.exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)

    conn = sqlite3.connect(str(dpath))
    try:
        detail = coach_service.get_thread(conn, thread_id)
    finally:
        conn.close()

    if detail is None:
        return api_error("NOT_FOUND", f"스레드를 찾을 수 없습니다: {thread_id}", 404)

    return api_ok(detail)


@api_bp.post("/coach/threads/<int:thread_id>/messages")
def post_coach_thread_messages(thread_id: int):
    dpath = db_path()
    if not dpath.exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)

    body = request.get_json(silent=True) or {}
    content = body.get("content")
    if not content:
        return api_error("INVALID_PARAM", "content가 필요합니다.", 400)

    conn = sqlite3.connect(str(dpath))
    try:
        if coach_service.get_thread(conn, thread_id) is None:
            return api_error("NOT_FOUND", f"스레드를 찾을 수 없습니다: {thread_id}", 404)

        config = load_config(user_id=get_current_user_id())
        message = coach_service.add_message(conn, thread_id, content, config=config)
    finally:
        conn.close()

    return api_ok({"message": message}, status=201)
