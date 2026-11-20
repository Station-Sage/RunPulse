"""`/api/v1/coach/plan/replan*` — 안전한 재계획 미리보기·적용·되돌리기 (ADR-035 부록 R)."""
from __future__ import annotations

import sqlite3

from flask import request

from src.services import garmin_cleanup as gc
from src.services import input_limits
from src.services import plan_replan_service as svc
from src.training.planner import WeekdaysRequired
from src.utils.user_context import db_path

from . import api_bp, api_error, api_ok
from .validation import float_field, int_field, json_object, parse_args

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
            "expect_anchor": src.get("expect_anchor"),
            "plan_method": (src.get("plan_method") or None),
            "rules_version": _num(src.get("rules_version"), "rules_version", True),
            "expect_rules_version": _num(src.get("expect_rules_version"), "expect_rules_version", True)}


def _run(fn):
    conn = _open()
    if conn is None:
        return api_error("NOT_FOUND", "running.db 없음", 503)
    try:
        return api_ok(fn(conn))
    except WeekdaysRequired as e:
        return api_error("INVALID_PARAM", str(e), 400, {"run_weekdays": str(e)})
    except svc.ReplanError as e:
        return api_error(e.code, e.message, _STATUS.get(e.code, 409), {"last": e.last} if e.last else None)
    finally:
        conn.close()


@api_bp.get("/coach/plan/replan/preview")
def replan_preview():
    try:
        p = _params(request.args)
    except ValueError as e:
        return api_error("BAD_REQUEST", str(e), 400)
    return _run(lambda c: svc.preview(c, p))


@api_bp.get("/coach/plan/methods")
def plan_methods():
    return _run(svc.methods_state)


@api_bp.get("/coach/plan/methods/recommend")
def plan_methods_recommend():
    from src.services import method_recommend as mr
    from src.utils.config import load_config
    from src.utils.user_context import get_current_user_id

    def _fn(conn):
        v = mr.view(conn)
        if v is None:
            raise svc.ReplanError("NO_GOAL", "활성 목표가 없습니다")
        pending = v["source"] == "rule" and mr.warm_in_background(str(db_path()), load_config(user_id=get_current_user_id()))
        return {**v, "pending": bool(pending)}
    return _run(_fn)


_DRAFT_ARGS = {"distance_km": float_field(0, input_limits.DISTANCE_KM_MAX, lo_exclusive=True, required=True),
               "run_days": int_field(1, 7), "target_time_sec": int_field(1, input_limits.TARGET_TIME_SEC_MAX),
               "weeks": int_field(*input_limits.WEEKS_RANGE)}


@api_bp.get("/coach/plan/methods/draft")
def plan_methods_draft():
    """생성 화면용 — 활성 목표 없이 거리·러닝 요일로 후보와 추천(AI 캐시 → 규칙 폴백)을 낸다."""
    from src.services import method_recommend_draft as md
    from src.utils.config import load_config
    from src.utils.user_context import get_current_user_id
    q, err = parse_args(_DRAFT_ARGS)
    if err:
        return err

    def _fn(conn):
        inp = md.build_draft_input(conn, q["distance_km"], q["run_days"], q["target_time_sec"], q["weeks"])
        v = md.view(conn, inp)
        pending = v["source"] == "rule" and md.warm(str(db_path()), load_config(user_id=get_current_user_id()), inp)
        return {"distance_label": inp["goal"]["distance"], "methods": [
            {k: c[k] for k in ("id", "label", "summary", "pros", "cons", "target_runners")} for c in inp["candidates"]],
            **v, "pending": bool(pending)}
    return _run(_fn)


@api_bp.get("/coach/plan/replan/last")
def replan_last():
    return _run(lambda c: (lambda e: {"last": e["last"], "entry": e})(svc.entry_state(c)))


@api_bp.post("/coach/plan/replan")
def replan_apply():
    raw, err = json_object()  # D-21
    if err:
        return err
    try:
        p = _params(raw)
    except ValueError as e:
        return api_error("BAD_REQUEST", str(e), 400)
    if not p["expect_anchor"]:
        return api_error("BAD_REQUEST", "expect_anchor 필요", 400)
    return _run(lambda c: svc.apply(c, p))


@api_bp.post("/coach/plan/replan/<int:replan_id>/undo")
def replan_undo(replan_id: int):
    return _run(lambda c: svc.undo(c, replan_id))


@api_bp.get("/coach/plan/replan/<int:replan_id>/garmin")
def replan_garmin_targets(replan_id: int):
    return _cleanup(lambda c: {"targets": gc.targets(c, replan_id)})


@api_bp.post("/coach/plan/replan/<int:replan_id>/garmin-cleanup")
def replan_garmin_cleanup(replan_id: int):
    def run(c):
        from src.training.garmin_push import _login
        from src.utils.config import load_config
        if not gc.targets(c, replan_id):
            return {"deleted": 0, "missing": 0, "failed": []}
        try:
            client = _login(load_config())
        except Exception as e:
            raise gc.CleanupError("GARMIN_LOGIN", f"Garmin 로그인 실패: {str(e)[:80]}")
        return gc.cleanup(c, replan_id, client)
    return _cleanup(run)


def _cleanup(fn):
    conn = _open()
    if conn is None:
        return api_error("NOT_FOUND", "running.db 없음", 503)
    try:
        return api_ok(fn(conn))
    except gc.CleanupError as e:
        return api_error(e.code, e.message, {"NO_REPLAN": 404, "GARMIN_LOGIN": 502}.get(e.code, 409))
    finally:
        conn.close()
