"""GET /api/v1/coach/plan/active, GET /api/v1/coach/plan/<int:goal_id>,
GET /api/v1/coach/plan/adjustment — Phase 7b."""
from __future__ import annotations

import sqlite3

from src.services import plan_service
from src.web.helpers import db_path

from . import api_bp, api_error, api_ok


@api_bp.get("/coach/plan/active")
def get_active_plan_route():
    dpath = db_path()
    if not dpath.exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)
    conn = sqlite3.connect(str(dpath))
    try:
        result = plan_service.get_active_plan(conn)
    finally:
        conn.close()
    if result is None:
        return api_error("NOT_FOUND", "활성 플랜 없음", 404)
    return api_ok(result)


@api_bp.get("/coach/plan/adjustment")
def get_plan_adjustment():
    dpath = db_path()
    if not dpath.exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)
    conn = sqlite3.connect(str(dpath))
    try:
        result = plan_service.get_todays_adjustment(conn)
    finally:
        conn.close()
    if result is None:
        return api_ok({"adjusted": False, "adjustment_reason": None})
    return api_ok(result)


@api_bp.get("/coach/plan/<int:goal_id>")
def get_plan_by_id(goal_id: int):
    dpath = db_path()
    if not dpath.exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)
    conn = sqlite3.connect(str(dpath))
    try:
        result = plan_service.get_active_plan(conn, goal_id=goal_id)
    finally:
        conn.close()
    if result is None:
        return api_error("NOT_FOUND", f"플랜 {goal_id} 없음", 404)
    return api_ok(result)
