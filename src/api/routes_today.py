"""GET /api/v1/today, GET /api/v1/today/checkin, POST /api/v1/today/checkin,
GET /api/v1/today/milestones, GET /api/v1/today/narrative, GET /api/v1/today/race-hub — Phase 7a/7b."""
from __future__ import annotations

import sqlite3

from flask import request

from src.services import data_health_service, milestone_service, race_hub_service, today_hero, today_service
from src.utils.config import load_config
from src.web.helpers import db_path, get_current_user_id

from . import api_bp, api_error, api_ok


@api_bp.get("/today")
def get_today():
    dpath = db_path()
    if not dpath.exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)

    conn = sqlite3.connect(str(dpath))
    try:
        status = today_service.get_today_status(conn)
        briefing = today_service.get_today_briefing(conn)
        recent_activities = today_service.get_recent_activities(conn, limit=3)
        checkin = today_service.get_todays_checkin(conn)
        data_health = data_health_service.get_load_coverage(conn)
        extras = today_hero.build_today_extras(conn, load_config(user_id=get_current_user_id()))
    finally:
        conn.close()

    # briefing은 기존 필드(headline/evidence)를 유지하고 state 계열을 얹는다(additive).
    briefing = {**briefing, **extras["briefing_state"]}
    return api_ok({
        "as_of": extras["as_of"],
        "readiness": extras["readiness"],
        "week_compliance": extras["week_compliance"],
        "race_summary": extras["race_summary"],
        "status": status,
        "briefing": briefing,
        "recent_activities": recent_activities,
        "checkin": checkin,
        "data_health": data_health,
    })


@api_bp.get("/today/checkin")
def get_today_checkin():
    dpath = db_path()
    if not dpath.exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)
    conn = sqlite3.connect(str(dpath))
    try:
        checkin = today_service.get_todays_checkin(conn)
    finally:
        conn.close()
    return api_ok({"checkin": checkin})


@api_bp.get("/today/milestones")
def get_today_milestones():
    dpath = db_path()
    if not dpath.exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)

    try:
        limit = int(request.args.get("limit", 10))
    except (ValueError, TypeError):
        limit = 10

    conn = sqlite3.connect(str(dpath))
    try:
        items = milestone_service.get_recent_milestones(conn, limit=limit)
    finally:
        conn.close()

    return api_ok({"milestones": items})


@api_bp.get("/today/narrative")
def get_today_narrative():
    dpath = db_path()
    if not dpath.exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)

    try:
        year_raw = request.args.get("year")
        month_raw = request.args.get("month")
        year = int(year_raw) if year_raw else None
        month = int(month_raw) if month_raw else None
    except (ValueError, TypeError):
        year, month = None, None
    # 하나만 있으면 무시(today_service 정책과 동일)
    if not (year and month):
        year, month = None, None

    config = load_config(user_id=get_current_user_id())
    conn = sqlite3.connect(str(dpath))
    try:
        result = today_service.get_today_narrative(conn, config=config, year=year, month=month)
    finally:
        conn.close()

    return api_ok(result)


@api_bp.get("/today/race-hub")
def get_today_race_hub():
    dpath = db_path()
    if not dpath.exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)

    conn = sqlite3.connect(str(dpath))
    try:
        result = race_hub_service.get_race_hub(conn)
    finally:
        conn.close()

    return api_ok(result)


@api_bp.post("/today/checkin")
def post_today_checkin():
    dpath = db_path()
    if not dpath.exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)

    body = request.get_json(silent=True) or {}
    conn = sqlite3.connect(str(dpath))
    try:
        result = today_service.save_checkin(
            conn,
            fatigue=body.get("fatigue"),
            pain=body.get("pain"),
            note=body.get("note"),
        )
    finally:
        conn.close()

    return api_ok({**result, "saved_at": result["created_at"]})
