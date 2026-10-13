"""GET /api/v1/coach/plan/* 조회 + POST /api/v1/coach/plan 생성 + GET /api/v1/coach/plan/adaptation — Phase 7b."""
from __future__ import annotations

import sqlite3
from datetime import date

from flask import current_app, request

from src.services import input_limits
from src.services import adaptation_service, plan_adjustment_service, plan_service, plan_template_service, weekly_adapt_job
from src.training import plan_readiness
from src.utils.user_context import db_path

from . import api_bp, api_error, api_ok
from .validation import date_field, float_field, int_field, parse_args, parse_body, str_field


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


_RACE_DATE = date_field(min_date=lambda: input_limits.race_date_window()[0],
                        max_date=lambda: input_limits.race_date_window()[1])
_TARGET_TIME = int_field(1, input_limits.TARGET_TIME_SEC_MAX)
_TEMPLATES_SCHEMA = {
    "distance_km": float_field(0, input_limits.DISTANCE_KM_MAX, lo_exclusive=True, required=True),
    "target_time_sec": _TARGET_TIME,
    "race_date": _RACE_DATE,
}


@api_bp.get("/coach/plan/templates")
def get_plan_templates():
    args, err = parse_args(_TEMPLATES_SCHEMA)
    if err:
        return err
    dpath = db_path()
    if not dpath.exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)
    conn = sqlite3.connect(str(dpath))
    try:
        templates = plan_template_service.get_static_plan_templates(
            conn, args["distance_km"], args["target_time_sec"], args["race_date"]
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


def _reported_km_field(key: str):
    """선택 입력(최근 주간 km·최장 롱런 km) — 0 초과 상한 이하, 소수 첫째 자리 반올림은 라우트에서."""
    return float_field(0, input_limits.REPORTED_KM_MAX[key], lo_exclusive=True)


_CREATE_PLAN_SCHEMA = {
    "distance_km": float_field(0, input_limits.DISTANCE_KM_MAX, lo_exclusive=True, required=True),
    "weeks": int_field(*input_limits.WEEKS_RANGE, required=True),
    "race_date": _RACE_DATE,
    "target_time_sec": _TARGET_TIME,
    "name": str_field(input_limits.PLAN_NAME_MAX),
    "recent_weekly_km": _reported_km_field("recent_weekly_km"),
    "recent_long_km": _reported_km_field("recent_long_km"),
}


@api_bp.post("/coach/plan")
def create_plan():
    body, err = parse_body(_CREATE_PLAN_SCHEMA)
    if err:
        return err
    weeks = body["weeks"]
    weekly_km, long_km = body["recent_weekly_km"], body["recent_long_km"]
    weekly_km = round(weekly_km, 1) if weekly_km is not None else None
    long_km = round(long_km, 1) if long_km is not None else None
    dpath = db_path()
    if not dpath.exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)
    conn = sqlite3.connect(str(dpath))
    try:
        goal_id = plan_template_service.create_plan_from_template(
            conn, body["distance_km"], body["race_date"], weeks, body["target_time_sec"], body["name"],
            recent_weekly_km=weekly_km, recent_long_km=long_km,
        )
        plan_weeks = conn.execute("SELECT plan_weeks FROM goals WHERE id=?", (goal_id,)).fetchone()[0]
        warnings = plan_readiness.plan_warnings(conn, goal_id)
    finally:
        conn.close()
    # 대회일까지 가능 주수보다 길게 요청하면 서비스가 줄여 만든다 — 조용한 보정 대신 알린다(SRV-7·SRV-11)
    meta = None
    if plan_weeks != weeks:
        meta = {"warnings": [{"code": "WEEKS_ADJUSTED", "requested": weeks, "applied": plan_weeks}]}
    return api_ok({"goal_id": goal_id, "plan_weeks": plan_weeks, "warnings": warnings}, meta=meta)
