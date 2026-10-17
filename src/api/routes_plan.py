"""GET /api/v1/coach/plan/* 조회 + POST /api/v1/coach/plan 생성 + GET /api/v1/coach/plan/adaptation — Phase 7b."""
from __future__ import annotations

import sqlite3
from datetime import date

from flask import current_app, request

from src.services.race_calendar_query import RaceError
from src.services import input_limits
from src.services import (adaptation_service, plan_overview_service, plan_adjustment_service, plan_restore, plan_service, plan_template_service,
                          weekly_adapt_job)
from src.training import plan_readiness
from src.training.planner_store import WeekdaysRequired
from src.utils.user_context import db_path

from . import api_bp, api_error, api_ok
from .validation import date_field, float_field, int_field, int_list_field, parse_args, parse_body, str_field


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


@api_bp.get("/coach/plan/restorable")
def get_restorable_plans_route():
    dpath = db_path()
    if not dpath.exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)
    conn = sqlite3.connect(str(dpath))
    try:
        return api_ok({"plans": plan_restore.list_restorable(conn)})
    finally:
        conn.close()


@api_bp.get("/coach/plan/<int:goal_id>/weeks")
def get_plan_weeks_route(goal_id: int):
    dpath = db_path()
    if not dpath.exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)
    conn = sqlite3.connect(str(dpath))
    try:
        result = plan_overview_service.get_plan_overview(conn, goal_id)
    finally:
        conn.close()
    if result is None:
        return api_error("NOT_FOUND", "목표 없음", 404)
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
    "run_weekdays": int_list_field(0, 6, max_items=7, required=True),
    "recent_weekly_km": _reported_km_field("recent_weekly_km"),
    "recent_long_km": _reported_km_field("recent_long_km"),
    "expect_active_goal_id": int_field(1, 2**31 - 1),
    "race_id": int_field(1, 2**31 - 1),
}


def _expect(body_in: dict, parsed: dict):
    """요청에 expect_active_goal_id 키가 있을 때만 검사 대상(없으면 기존 동작 — 클라이언트 구버전 호환)."""
    return parsed["expect_active_goal_id"] if "expect_active_goal_id" in body_in else plan_template_service._UNSET


def _conflict(exc: plan_template_service.PlanConflict):
    return api_error("ACTIVE_PLAN_EXISTS", str(exc), 409, {"current": exc.current})


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
            recent_weekly_km=weekly_km, recent_long_km=long_km, run_weekdays=body["run_weekdays"],
            expect_active_goal_id=_expect(request.get_json(silent=True) or {}, body), race_id=body["race_id"],
        )
        plan_weeks = conn.execute("SELECT plan_weeks FROM goals WHERE id=?", (goal_id,)).fetchone()[0]
        warnings = plan_readiness.plan_warnings(conn, goal_id)
    except WeekdaysRequired as exc:
        return api_error("INVALID_PARAM", str(exc), 400, {"run_weekdays": str(exc)})
    except plan_template_service.PlanConflict as exc:
        return _conflict(exc)
    except RaceError as exc:
        return api_error(exc.code, str(exc), exc.http, exc.extra or None)
    finally:
        conn.close()
    # 대회일까지 가능 주수보다 길게 요청하면 서비스가 줄여 만든다 — 조용한 보정 대신 알린다(SRV-7·SRV-11)
    meta = None
    if plan_weeks != weeks:
        meta = {"warnings": [{"code": "WEEKS_ADJUSTED", "requested": weeks, "applied": plan_weeks}]}
    return api_ok({"goal_id": goal_id, "plan_weeks": plan_weeks, "warnings": warnings}, meta=meta)


@api_bp.post("/coach/plan/<int:goal_id>/restore")
def restore_plan_route(goal_id: int):
    """취소된 과거 플랜을 복원(PLN-43). 활성 플랜이 있으면 expect_active_goal_id 확인 후 교체, 불일치 시 409."""
    raw = request.get_json(silent=True) or {}
    expect = raw.get("expect_active_goal_id", plan_template_service._UNSET)
    if expect is not plan_template_service._UNSET and expect is not None and not isinstance(expect, int):
        return api_error("BAD_REQUEST", "expect_active_goal_id 는 정수여야 합니다", 400)
    dpath = db_path()
    if not dpath.exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)
    conn = sqlite3.connect(str(dpath))
    try:
        return api_ok(plan_restore.restore_plan(conn, goal_id, expect))
    except plan_template_service.PlanConflict as exc:
        return _conflict(exc)
    except plan_restore.RestoreError as exc:
        return api_error(exc.code, str(exc), 404 if exc.code == "NOT_FOUND" else 409)
    finally:
        conn.close()
