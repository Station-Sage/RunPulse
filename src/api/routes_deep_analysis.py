"""`/api/v1/coach/deep*` — 사용자 요청 심화 분석 시작·조회·취소 (V2-AI-CLAUDE-QUEUE E5-d)."""
from __future__ import annotations

from flask import request

from src.ai import provider_claude_queue as pcq
from src.services import deep_analysis as da
from src.utils.config import load_config
from src.utils.user_context import db_path

from . import api_bp, api_error, api_ok
from .routes_plan_replan import _open
from .validation import json_object


@api_bp.get("/coach/deep")
def deep_state():
    conn = _open()
    if conn is None:
        return api_error("NOT_FOUND", "running.db 없음", 503)
    try:
        aid = da.pick_activity_id(conn, request.args.get("activity_id", type=int))
        run = da.run_state(str(db_path()))
        if run and run.get("activity_id") != aid:
            run = None
        return api_ok({"available": pcq.available(conn, load_config()), "activity_id": aid, "run": run,
                       "result": da.get_cached(conn, aid) if aid else None})
    finally:
        conn.close()


@api_bp.post("/coach/deep")
def deep_start():
    raw, err = json_object()
    if err:
        return err
    conn = _open()
    if conn is None:
        return api_error("NOT_FOUND", "running.db 없음", 503)
    try:
        cfg = load_config()
        if not pcq.available(conn, cfg):
            return api_error("UNAVAILABLE", "AI 큐를 사용할 수 없습니다", 409)
        aid = da.pick_activity_id(conn, raw.get("activity_id"))
        if not aid:
            return api_error("NOT_FOUND", "분석할 활동이 없습니다", 404)
    finally:
        conn.close()
    started = da.start_background(str(db_path()), cfg, aid)
    return api_ok({"started": started, "activity_id": aid}, 202)


@api_bp.post("/coach/deep/cancel")
def deep_cancel():
    return api_ok({"cancelled": da.cancel(str(db_path()))})
