"""`/api/v1/coach/plan/adjustments*` — 계획 조정 수락·되돌리기·이력 (ADR-035)."""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from flask import request

from src.services import plan_adjustment_service as svc
from src.training import week_compliance
from src.web.helpers import db_path

from . import api_bp, api_error, api_ok


def _open() -> sqlite3.Connection | None:
    p = db_path()
    return sqlite3.connect(str(p)) if p.exists() else None


def _week_planned_km(conn: sqlite3.Connection, day: str) -> float:
    d = date.fromisoformat(day)
    ws = d - timedelta(days=d.weekday())
    c = week_compliance.compute(conn, ws, ws + timedelta(days=6), None, d)
    return round(sum(x.get("planned_km") or 0 for x in c["days"]), 1)


def _conflict(e: svc.AdjustmentConflict):
    if e.code == "NOT_FOUND":
        return api_error("NOT_FOUND", str(e), 404)
    return api_error("CONFLICT", str(e), 409, {"reason": e.code, "current": e.current})


def _decide(adj_id: int, action: str):
    conn = _open()
    if conn is None:
        return api_error("NOT_FOUND", "running.db 없음", 503)
    body = request.get_json(silent=True) or {}
    via = body.get("via")
    try:
        cur = svc._get(conn, adj_id)
        before_km = _week_planned_km(conn, cur["date"]) if cur else None
        if action == "accept":
            try:
                rev = int(body["rev"])
            except (KeyError, TypeError, ValueError):
                return api_error("BAD_REQUEST", "rev 필요", 400)
            adj = svc.accept(conn, adj_id, rev=rev, via=via)
        else:
            adj = svc.revert(conn, adj_id, via=via)
        d = date.fromisoformat(adj["date"])
        ws = d - timedelta(days=d.weekday())
        compliance = week_compliance.compute(conn, ws, ws + timedelta(days=6), None, d)["compliance"]
        return api_ok({"adjustment": adj, "compliance": compliance,
                       "week_planned_km": {"before": before_km, "after": _week_planned_km(conn, adj["date"])}})
    except svc.AdjustmentConflict as e:
        return _conflict(e)
    finally:
        conn.close()


@api_bp.post("/coach/plan/adjustments/<int:adj_id>/accept")
def accept_plan_adjustment(adj_id: int):
    return _decide(adj_id, "accept")


@api_bp.post("/coach/plan/adjustments/<int:adj_id>/revert")
def revert_plan_adjustment(adj_id: int):
    return _decide(adj_id, "revert")


@api_bp.get("/coach/plan/<int:goal_id>/adjustments")
def list_plan_adjustments(goal_id: int):
    start, end = request.args.get("from"), request.args.get("to")
    try:
        date.fromisoformat(start or "")
        date.fromisoformat(end or "")
    except ValueError:
        return api_error("BAD_REQUEST", "from/to(YYYY-MM-DD) 필요", 400)
    conn = _open()
    if conn is None:
        return api_error("NOT_FOUND", "running.db 없음", 503)
    try:
        return api_ok({"adjustments": svc.list_adjustments(conn, goal_id=goal_id, start=start, end=end)})
    finally:
        conn.close()
