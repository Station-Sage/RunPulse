"""/api/v1/coach — threads(+:id, +:id/messages) · messages(:id, /stream, /cancel, /regenerate) · suggestions · engine · consent.

전송 계열은 pending 행을 즉시 돌려주고 coach_async 워커가 답변을 만든다(design §6.2).
"""
from __future__ import annotations

import sqlite3

from flask import Response, request, stream_with_context

from src.services import coach_async, coach_consent, coach_engine_health, coach_service
from src.utils.config import load_config
from src.web.helpers import db_path, get_current_user_id

from . import api_bp, api_error, api_ok


def _message_input(body: dict, text_key: str):
    """(text, chip_id, error_response) — 본문 또는 알려진 chip_id 중 하나는 있어야 한다."""
    from src.ai.coach_rule_types import CHIP_TEXT
    text = (body.get(text_key) or "").strip() or None
    chip_id = body.get("chip_id") or None
    if chip_id is not None and chip_id not in CHIP_TEXT:
        return None, None, api_error("INVALID_PARAM", f"알 수 없는 chip_id: {chip_id}", 400)
    if not text and not chip_id:
        return None, None, api_error("INVALID_PARAM", f"{text_key} 또는 chip_id가 필요합니다.", 400)
    return text, chip_id, None


@api_bp.get("/coach/suggestions")
def get_coach_suggestions():
    """지금 규칙 핸들러로 답할 수 있는 추천 칩만 — at=home(기본)."""
    dpath = db_path()
    if not dpath.exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)

    from src.ai.coach_rule_handlers import suggestion_chips
    conn = sqlite3.connect(str(dpath))
    try:
        suggestions = suggestion_chips(conn)
    finally:
        conn.close()
    return api_ok({"suggestions": suggestions})


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
    """새 대화 — 스레드·사용자 메시지·pending 답변을 즉시 돌려주고 답변 생성은 백그라운드에서 시작한다."""
    dpath = db_path()
    if not dpath.exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)

    body = request.get_json(silent=True) or {}
    initial_message, chip_id, err = _message_input(body, "initial_message")
    if err:
        return err

    config = load_config(user_id=get_current_user_id())
    conn = sqlite3.connect(str(dpath))
    try:
        sent = coach_service.create_thread(conn, initial_message, config=config, chip_id=chip_id,
                                           client_msg_id=body.get("client_msg_id") or None,
                                           context=body.get("context"))
    finally:
        conn.close()

    created = sent.pop("created")
    if created:
        coach_async.start(dpath, config, sent["assistant_message"]["id"])
    return api_ok(sent, status=201 if created else 200)


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
    """메시지 전송 — 사용자 메시지·pending 답변을 즉시 돌려주고 답변 생성은 백그라운드에서 시작한다."""
    dpath = db_path()
    if not dpath.exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)

    body = request.get_json(silent=True) or {}
    content, chip_id, err = _message_input(body, "content")
    if err:
        return err

    config = load_config(user_id=get_current_user_id())
    conn = sqlite3.connect(str(dpath))
    try:
        if coach_service.get_thread(conn, thread_id) is None:
            return api_error("NOT_FOUND", f"스레드를 찾을 수 없습니다: {thread_id}", 404)
        sent = coach_service.add_message(conn, thread_id, content, config=config, chip_id=chip_id,
                                         client_msg_id=body.get("client_msg_id") or None)
    finally:
        conn.close()

    created = sent.pop("created")
    if created:
        coach_async.start(dpath, config, sent["assistant_message"]["id"])
    return api_ok(sent, status=201 if created else 200)


@api_bp.get("/coach/messages/<int:message_id>")
def get_coach_message(message_id: int):
    """폴링용 — 스트림이 끊긴 클라이언트가 최종 상태를 확인한다."""
    dpath = db_path()
    if not dpath.exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)

    conn = sqlite3.connect(str(dpath))
    try:
        message = coach_service.get_message(conn, message_id)
    finally:
        conn.close()
    if message is None:
        return api_error("NOT_FOUND", f"메시지를 찾을 수 없습니다: {message_id}", 404)
    return api_ok({"message": message})


@api_bp.get("/coach/messages/<int:message_id>/stream")
def get_coach_message_stream(message_id: int):
    """SSE — stage · delta · evidence · done · error. Last-Event-ID로 이어받는다."""
    dpath = db_path()
    if not dpath.exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)

    raw = request.headers.get("Last-Event-ID") or request.args.get("last_event_id") or "0"
    last_id = int(raw) if raw.isdigit() else 0
    return Response(stream_with_context(coach_async.stream(dpath, message_id, last_id)),
                    mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@api_bp.post("/coach/messages/<int:message_id>/cancel")
def post_coach_cancel(message_id: int):
    dpath = db_path()
    if not dpath.exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)

    status = coach_async.cancel(dpath, message_id)
    if status is None:
        return api_error("NOT_FOUND", f"메시지를 찾을 수 없습니다: {message_id}", 404)
    return api_ok({"status": status})


@api_bp.post("/coach/messages/<int:message_id>/regenerate")
def post_coach_regenerate(message_id: int):
    """다시 생성 — mode: 'ai'(기본) | 'rule'(기본 답변). 새 pending 메시지를 돌려주고 생성을 시작한다."""
    dpath = db_path()
    if not dpath.exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)

    mode = (request.get_json(silent=True) or {}).get("mode") or "ai"
    if mode not in ("ai", "rule"):
        return api_error("INVALID_PARAM", "mode는 ai 또는 rule이어야 합니다.", 400)

    config = load_config(user_id=get_current_user_id())
    conn = sqlite3.connect(str(dpath))
    try:
        row = conn.execute("SELECT thread_id FROM chat_messages WHERE id = ? AND role = 'assistant'",
                           (message_id,)).fetchone()
        message = coach_service.regenerate(conn, row[0], message_id, config=config) if row else None
    finally:
        conn.close()

    if message is None:
        return api_error("NOT_FOUND", "다시 생성할 메시지를 찾을 수 없습니다.", 404)
    coach_async.start(dpath, config, message["id"], mode=mode)
    return api_ok({"message": message})


@api_bp.get("/coach/engine")
def get_coach_engine():
    dpath = db_path()
    if not dpath.exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)

    config = load_config(user_id=get_current_user_id())
    conn = sqlite3.connect(str(dpath))
    try:
        payload = coach_engine_health.get_engine(conn, config)
    finally:
        conn.close()
    return api_ok(payload)


@api_bp.put("/coach/consent")
def put_coach_consent():
    dpath = db_path()
    if not dpath.exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)

    body = request.get_json(silent=True) or {}
    provider = body.get("provider")
    if not provider:
        return api_error("INVALID_PARAM", "provider가 필요합니다.", 400)

    conn = sqlite3.connect(str(dpath))
    try:
        consent = coach_consent.save_consent(
            conn, provider,
            exclude_notes=bool(body.get("exclude_notes", False)),
            tools_enabled=bool(body.get("tools_enabled", True)),
            fallback_enabled=bool(body.get("fallback_enabled", True)),
        )
    except ValueError as exc:
        return api_error("INVALID_PARAM", str(exc), 400)
    finally:
        conn.close()
    return api_ok({"consent": consent})
