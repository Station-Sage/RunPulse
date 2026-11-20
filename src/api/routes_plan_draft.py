"""`/api/v1/coach/plan/draft*` — AI 플랜 초안 생성·조회·적용 (V2-AI-CLAUDE-QUEUE E5-c)."""
from __future__ import annotations

from flask import request

from src.ai import provider_claude_queue as pcq
from src.services import plan_draft as pd
from src.services import plan_replan_service as svc
from src.utils.config import load_config
from src.utils.user_context import db_path

from . import api_bp, api_error, api_ok
from .routes_plan_replan import _STATUS, _open, _params
from .validation import json_object


@api_bp.get("/coach/plan/draft")
def plan_draft_state():
    conn = _open()
    if conn is None:
        return api_error("NOT_FOUND", "running.db 없음", 503)
    try:
        cur = pd.latest(conn) or {}
        running = pd.is_running(str(db_path()))
        return api_ok({"available": pcq.available(conn, load_config()), "running": running,
                       "state": "running" if running else cur.get("state", "none"), "summary": cur.get("summary"),
                       "reason": cur.get("reason"), "changed": cur.get("changed"), "anchor_monday": cur.get("anchor_monday")})
    finally:
        conn.close()


@api_bp.post("/coach/plan/draft")
def plan_draft_start():
    raw, err = json_object()
    if err:
        return err
    try:
        p = _params(raw)
    except ValueError as e:
        return api_error("BAD_REQUEST", str(e), 400)
    conn = _open()
    if conn is None:
        return api_error("NOT_FOUND", "running.db 없음", 503)
    try:
        cfg = load_config()
        if not pcq.available(conn, cfg):
            return api_error("UNAVAILABLE", "AI 큐를 사용할 수 없습니다", 409)
    finally:
        conn.close()
    params = {k: p[k] for k in ("recent_weekly_km", "recent_long_km", "target_time_sec", "plan_method") if p.get(k)}
    started = pd.start_background(str(db_path()), cfg, params)
    return api_ok({"started": started, "running": True}, 202)


@api_bp.post("/coach/plan/draft/apply")
def plan_draft_apply():
    raw, err = json_object()
    if err:
        return err
    anchor = raw.get("expect_anchor")
    if not anchor:
        return api_error("BAD_REQUEST", "expect_anchor 필요", 400)
    conn = _open()
    if conn is None:
        return api_error("NOT_FOUND", "running.db 없음", 503)
    try:
        return api_ok(pd.apply_draft(conn, anchor))
    except svc.ReplanError as e:
        return api_error(e.code, e.message, {**_STATUS, "NO_DRAFT": 404}.get(e.code, 409))
    finally:
        conn.close()
