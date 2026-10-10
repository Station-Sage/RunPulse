"""GET /api/v1/coach/plan/* 조회 + POST /api/v1/coach/plan 생성 + GET /api/v1/coach/plan/adaptation — Phase 7b."""
from __future__ import annotations

import sqlite3
from datetime import date

from flask import current_app, request

from src.services import adaptation_service, plan_adjustment_service, plan_service, plan_template_service, weekly_adapt_job
from src.training import plan_readiness
from src.web.helpers import db_path

from . import api_bp, api_error, api_ok


@api_bp.get("/coach/plan/active")
def get_active_plan_route():
    dpath = db_path()
    if not dpath.exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)
    conn = sqlite3.connect(str(dpath))
    try:
        try:
            weekly_adapt_job.run(conn)
        except Exception:
            current_app.logger.exception("weekly_adapt_job 실패 — 계획 조회는 계속")
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
        day = plan_adjustment_service.get_day_adjustment(conn, date.today().isoformat())
        user_adj = plan_adjustment_service.get_user_adjustment(conn, date.today().isoformat())
    finally:
        conn.close()
    base = result if result is not None else {"adjusted": False, "adjustment_reason": None}
    return api_ok({**base, "state": day["state"], "adjustment": day["adjustment"],
                    "user_adjustment": user_adj})


@api_bp.get("/coach/plan/adaptation")
def get_plan_adaptation():
    dpath = db_path()
    if not dpath.exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)
    conn = sqlite3.connect(str(dpath))
    try:
        result = adaptation_service.get_adaptation_status(conn)
    finally:
        conn.close()
    return api_ok({"adaptation": result})


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
    race_date = request.args.get("race_date") or None
    dpath = db_path()
    if not dpath.exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)
    conn = sqlite3.connect(str(dpath))
    try:
        templates = plan_template_service.get_static_plan_templates(
            conn, distance_km, target_time_sec, race_date
        )
    finally:
        conn.close()
    return api_ok(templates)


@api_bp.get("/coach/plan/<int:goal_id>/session/<session_date>")
def get_session_detail_route(goal_id: int, session_date: str):
    dpath = db_path()
    if not dpath.exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)
    conn = sqlite3.connect(str(dpath))
    try:
        result = plan_service.get_session_detail(conn, goal_id, session_date)
    finally:
        conn.close()
    if result is None:
        return api_error("NOT_FOUND", f"세션 {session_date} 없음", 404)
    return api_ok(result)


@api_bp.post("/coach/plan/session/<session_date>/note")
def save_session_note_route(session_date: str):
    body = request.get_json(silent=True) or {}
    note = body.get("note", "")
    if not isinstance(note, str) or not note.strip():
        return api_error("BAD_REQUEST", "note는 빈 문자열일 수 없습니다", 400)
    dpath = db_path()
    if not dpath.exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)
    conn = sqlite3.connect(str(dpath))
    try:
        plan_service.save_session_note(conn, session_date, note)
    finally:
        conn.close()
    return api_ok({"note": note})


_REPORTED_MAX_KM = {"recent_weekly_km": 300.0, "recent_long_km": 60.0}


def _reported_km(body: dict, key: str) -> tuple[float | None, str | None]:
    """선택 입력(최근 주간 km·최장 롱런 km) 검증. 비어 있으면 None, 범위 밖이면 오류 문구."""
    raw = body.get(key)
    if raw is None or raw == "":
        return None, None
    try:
        val = float(raw)
    except (TypeError, ValueError):
        return None, f"{key} 는 숫자여야 합니다"
    if not 0 < val <= _REPORTED_MAX_KM[key]:
        return None, f"{key} 는 0 초과 {_REPORTED_MAX_KM[key]:.0f} 이하"
    return round(val, 1), None


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
    weekly_km, err_w = _reported_km(body, "recent_weekly_km")
    long_km, err_l = _reported_km(body, "recent_long_km")
    if err_w or err_l:
        return api_error("BAD_REQUEST", err_w or err_l, 400)
    dpath = db_path()
    if not dpath.exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)
    conn = sqlite3.connect(str(dpath))
    try:
        goal_id = plan_template_service.create_plan_from_template(
            conn, float(distance_km), race_date, int(weeks), target_time_sec, name,
            recent_weekly_km=weekly_km, recent_long_km=long_km,
        )
        plan_weeks = conn.execute("SELECT plan_weeks FROM goals WHERE id=?", (goal_id,)).fetchone()[0]
        warnings = plan_readiness.plan_warnings(conn, goal_id)
    finally:
        conn.close()
    return api_ok({"goal_id": goal_id, "plan_weeks": plan_weeks, "warnings": warnings})
