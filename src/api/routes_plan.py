"""GET /api/v1/coach/plan/* 조회 + POST /api/v1/coach/plan 생성 — Phase 7b."""
from __future__ import annotations

import sqlite3

from flask import request

from src.services import plan_service, plan_template_service
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


@api_bp.get("/coach/plan/templates")
def get_plan_templates():
    distance_km = request.args.get("distance_km", type=float)
    if distance_km is None:
        return api_error("BAD_REQUEST", "distance_km 필수", 400)
    target_time_sec = request.args.get("target_time_sec", type=int)
    dpath = db_path()
    if not dpath.exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)
    conn = sqlite3.connect(str(dpath))
    try:
        templates = plan_template_service.get_static_plan_templates(
            conn, distance_km, target_time_sec
        )
    finally:
        conn.close()
    return api_ok(templates)


@api_bp.post("/coach/plan")
def create_plan():
    body = request.get_json(silent=True) or {}
    distance_km = body.get("distance_km")
    if distance_km is None:
        return api_error("BAD_REQUEST", "distance_km 필수", 400)
    weeks = body.get("weeks")
    if weeks is None:
        return api_error("BAD_REQUEST", "weeks 필수", 400)
    race_date = body.get("race_date") or None
    target_time_sec = body.get("target_time_sec") or None
    name = body.get("name") or None
    dpath = db_path()
    if not dpath.exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)
    conn = sqlite3.connect(str(dpath))
    try:
        goal_id = plan_template_service.create_plan_from_template(
            conn, float(distance_km), race_date, int(weeks), target_time_sec, name
        )
    finally:
        conn.close()
    return api_ok({"goal_id": goal_id})
