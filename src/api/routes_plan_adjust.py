"""`/api/v1/coach/plan/adjustments*` — 계획 조정 수락·되돌리기·이력 (ADR-035)."""
from __future__ import annotations

from src.training.goals import get_active_goal
import sqlite3
from datetime import date, timedelta

from flask import request

from src.services import plan_adjustment_service as svc
from src.services import plan_advisory, plan_load, plan_pain
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


def _load_delta(conn: sqlite3.Connection, workout_id: int, op: str, params: dict) -> dict | None:
    after = svc.preview_after(conn, workout_id, plan_pain.resolve(op, params), params)
    return plan_load.load_delta(conn, workout_id, after, today=date.today().isoformat())


def _advisories(conn: sqlite3.Connection, adj_id: int, delta: dict | None) -> list[dict]:
    today = date.today().isoformat()
    return [a for a in [plan_pain.repeat(conn, today)] if a] + plan_advisory.issue(conn, adj_id, today, delta)


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


@api_bp.post("/coach/plan/workouts/<int:workout_id>/action")
def plan_workout_action(workout_id: int):
    body = request.get_json(silent=True) or {}
    conn = _open()
    if conn is None:
        return api_error("NOT_FOUND", "running.db 없음", 503)
    try:
        before_km = None
        r = conn.execute("SELECT date FROM planned_workouts WHERE id = ?", (workout_id,)).fetchone()
        if r:
            before_km = _week_planned_km(conn, r[0])
        try:
            delta = _load_delta(conn, workout_id, str(body.get("op") or ""), body)
            adj = svc.create_user_adjustment(conn, workout_id, str(body.get("op") or ""), body,
                                             source="user", via=body.get("via"))
        except ValueError as e:
            return api_error("BAD_REQUEST", str(e), 400)
        d = date.fromisoformat(adj["date"])
        ws = d - timedelta(days=d.weekday())
        compliance = week_compliance.compute(conn, ws, ws + timedelta(days=6), None, d)["compliance"]
        return api_ok({"adjustment": adj, "compliance": compliance,
                       "week_planned_km": {"before": before_km, "after": _week_planned_km(conn, adj["date"])},
                       "load_delta": delta,
                       "advisories": _advisories(conn, adj["id"], delta)}, 201)
    except svc.AdjustmentConflict as e:
        return _conflict(e)
    finally:
        conn.close()


@api_bp.get("/coach/plan/workouts/<int:workout_id>/action/preview")
def plan_workout_action_preview(workout_id: int):
    params: dict = {k: v for k, v in request.args.items()}
    if "pain_sites" in params:
        params["pain_sites"] = [x for x in params["pain_sites"].split(",") if x]
    for k in ("pct", "reps"):
        if k in params:
            try:
                params[k] = int(params[k])
            except ValueError:
                return api_error("BAD_REQUEST", f"{k} 는 정수", 400)
    conn = _open()
    if conn is None:
        return api_error("NOT_FOUND", "running.db 없음", 503)
    try:
        return api_ok({"load_delta": _load_delta(conn, workout_id, params.get("op", ""), params)})
    except ValueError as e:
        return api_error("BAD_REQUEST", str(e), 400)
    except svc.AdjustmentConflict as e:
        return _conflict(e)
    finally:
        conn.close()


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


def _replan_link(conn: sqlite3.Connection, today: date) -> dict:
    g = get_active_goal(conn)
    link: dict = {"distance_km": g["distance_km"], "race_date": g["race_date"], "target_time_sec": g["target_time_sec"]} if g else {}
    ws = today - timedelta(days=today.weekday())
    kms = []
    for k in (1, 2):
        s = ws - timedelta(weeks=k)
        kms.append(week_compliance.compute(conn, s, s + timedelta(days=6), None, today)["compliance"]["volume"]["actual_km"])
    if any(kms):
        link["recent_weekly_km"] = round(sum(kms) / 2, 1)
    return link


@api_bp.get("/coach/plan/advisories")
def plan_advisories():
    try:
        day = date.fromisoformat(request.args.get("date", ""))
    except ValueError:
        return api_error("BAD_REQUEST", "date(YYYY-MM-DD) 필요", 400)
    conn = _open()
    if conn is None:
        return api_error("NOT_FOUND", "running.db 없음", 503)
    try:
        since = (day - timedelta(days=3)).isoformat()
        if plan_pain._pain_rows(conn, since, day.isoformat()):
            return api_ok({"advisories": []})
        items = plan_advisory.compute(conn, day.isoformat(), None)
        for a in items:
            if a["code"] == "REPLAN":
                a["link"] = _replan_link(conn, day)
        return api_ok({"advisories": items})
    finally:
        conn.close()
