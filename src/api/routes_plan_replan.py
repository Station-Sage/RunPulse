"""`/api/v1/coach/plan/replan*` — 안전한 재계획 미리보기·적용·되돌리기 (ADR-035 부록 R)."""
from __future__ import annotations

import sqlite3

from flask import request

from src.services import plan_replan_service as svc
from src.web.helpers import db_path

from . import api_bp, api_error, api_ok

_STATUS = {"NO_GOAL": 404}


def _open() -> sqlite3.Connection | None:
    p = db_path()
    return sqlite3.connect(str(p)) if p.exists() else None


def _num(v, name: str, integer: bool = False):
    if v in (None, ""):
        return None
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise ValueError(f"{name} 는 숫자여야 합니다")
    if x <= 0:
        raise ValueError(f"{name} 는 0보다 커야 합니다")
    return int(x) if integer else x


def _params(src) -> dict:
    return {"recent_weekly_km": _num(src.get("recent_weekly_km"), "recent_weekly_km"),
            "recent_long_km": _num(src.get("recent_long_km"), "recent_long_km"),
            "target_time_sec": _num(src.get("target_time_sec"), "target_time_sec", True),
            "expect_anchor": src.get("expect_anchor")}


def _run(fn):
    conn = _open()
    if conn is None:
        return api_error("NOT_FOUND", "running.db 없음", 503)
    try:
        return api_ok(fn(conn))
    except svc.ReplanError as e:
        return api_error(e.code, e.message, _STATUS.get(e.code, 409))
    finally:
        conn.close()


@api_bp.get("/coach/plan/replan/preview")
def replan_preview():
    try:
        p = _params(request.args)
    except ValueError as e:
        return api_error("BAD_REQUEST", str(e), 400)
    return _run(lambda c: svc.preview(c, p))


@api_bp.post("/coach/plan/replan")
def replan_apply():
    try:
        p = _params(request.get_json(silent=True) or {})
    except ValueError as e:
        return api_error("BAD_REQUEST", str(e), 400)
    if not p["expect_anchor"]:
        return api_error("BAD_REQUEST", "expect_anchor 필요", 400)
    return _run(lambda c: svc.apply(c, p))


@api_bp.post("/coach/plan/replan/<int:replan_id>/undo")
def replan_undo(replan_id: int):
    return _run(lambda c: svc.undo(c, replan_id))
