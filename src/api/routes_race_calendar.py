"""`/api/v1/race-calendar*` — 대회 캘린더 CRUD·영향 미리보기·플랜 반영·복원·되돌리기 (RC-c, S4-28).

새 비즈니스 로직 없음 — src/services/race_calendar_*·race_plan_link 를 호출하고 RaceError 를 봉투로 옮긴다.
쓰기 후 commit 은 이 계층이 한다(서비스는 commit 하지 않음). 오류는 RaceError.http·code(+extra → details).
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager

from flask import request

from src.services import input_limits as lim
from src.services import race_calendar_query as q
from src.services import race_calendar_service as svc
from src.services import race_calendar_state as state
from src.services import race_plan_link as link
from src.utils.reference_day import reference_today
from src.utils.user_context import db_path

from . import api_bp, api_error, api_ok
from .validation import bool_field, date_field, dict_field, enum_field, float_field, int_field, parse_body, str_field

_FIELDS = {
    "name": str_field(lim.PLAN_NAME_MAX),
    "race_date": date_field(),
    "distance_km": float_field(0, lim.DISTANCE_KM_MAX, lo_exclusive=True),
    "priority": enum_field(("A", "B", "C")),
    "goal_type": enum_field(("finish", "time", "pb")),
    "goal_value": int_field(1, 24 * 3600),
    "taper_days": int_field(0, 28),
    "recovery_days": int_field(0, 28),
    "note": str_field(500),
}
_GOAL_LINK = dict_field({"race_id": int_field(1, 2**31 - 1)})
_RESTORE = {"confirm_past": bool_field(), "demote_existing_a": bool_field(),
            "goal_link": _GOAL_LINK}
_REOPEN = {"demote_existing_a": bool_field(), "goal_link": _GOAL_LINK}
_CANCEL = {"cancel_goal": bool_field()}
_PLAN = {"action": enum_field(("adapt", "later", "no_adapt", "undo"), required=True)}


@contextmanager
def _conn():
    p = db_path()
    if not p.exists():
        yield None
        return
    c = sqlite3.connect(str(p))
    try:
        yield c
    finally:
        c.close()


def _today(conn) -> str:
    return reference_today(conn)[0]


def _fail(exc: q.RaceError):
    return api_error(exc.code, str(exc), exc.http, getattr(exc, "extra", None) or None)


def _run(fn, *, write: bool = True):
    """DB 열기 → fn(conn, today) → commit/rollback → RaceError 변환."""
    with _conn() as conn:
        if conn is None:
            return api_error("NOT_FOUND", "running.db 없음", 503)
        try:
            out = fn(conn, _today(conn))
            if write:
                conn.commit()
            return out
        except q.RaceError as exc:
            conn.rollback()
            return _fail(exc)


def _raw() -> dict:
    return request.get_json(silent=True) or {}


def _present(clean: dict) -> dict:
    """PATCH 용 — 요청 본문에 실제로 있던 키만 남긴다(스키마 기본값 None 이 덮어쓰지 않게)."""
    raw = _raw()
    return {k: v for k, v in clean.items() if k in raw and v is not None}


def _view(conn, race: dict, today: str) -> dict:
    return {**race, "needs_review": q.is_needs_review(race, today), "goal_linked": q.is_goal_race(conn, race["id"])}


@api_bp.get("/race-calendar")
def list_races():
    def go(conn, today):
        z = q.list_zones(conn, today)
        z["basis"] = reference_today(conn)[1]
        g = conn.execute("SELECT race_id FROM goals WHERE status='active' AND race_id IS NOT NULL LIMIT 1").fetchone()
        z["goal_race_id"] = g[0] if g else None
        return api_ok(z)
    return _run(go, write=False)


@api_bp.post("/race-calendar")
def create_race():
    body, err = parse_body(_FIELDS)
    if err:
        return err
    data = {k: v for k, v in body.items() if v is not None}

    def go(conn, today):
        race = svc.add(conn, data)
        return api_ok(_view(conn, race, today), 201)
    return _run(go)


@api_bp.get("/race-calendar/<int:race_id>")
def get_race(race_id: int):
    return _run(lambda conn, today: api_ok(_view(conn, q.require(conn, race_id), today)), write=False)


@api_bp.patch("/race-calendar/<int:race_id>")
def update_race(race_id: int):
    body, err = parse_body(_FIELDS)
    if err:
        return err
    changes = _present(body)

    def go(conn, today):
        return api_ok(_view(conn, svc.update(conn, race_id, changes), today))
    return _run(go)


@api_bp.delete("/race-calendar/<int:race_id>")
def cancel_race(race_id: int):
    body, err = parse_body(_CANCEL, require_json=False)
    if err:
        return err
    args = request.args.get("cancel_goal") in ("1", "true")

    def go(conn, today):
        out = svc.cancel(conn, race_id, cancel_goal=bool(body.get("cancel_goal")) or args)
        return api_ok(_view(conn, out, today) | {"goal_cancelled": bool(out.get("goal_cancelled"))})
    return _run(go)


@api_bp.get("/race-calendar/<int:race_id>/impact")
def race_impact_route(race_id: int):
    def go(conn, today):
        rows = link.preview(conn, race_id, today)
        return api_ok({"race_id": race_id, "n": len(rows), "changes": rows})
    return _run(go, write=False)


@api_bp.post("/race-calendar/<int:race_id>/plan")
def race_plan_route(race_id: int):
    body, err = parse_body(_PLAN)
    if err:
        return err
    action = body["action"]

    def go(conn, today):
        race = q.require(conn, race_id)
        res = None
        if action == "undo":
            if race["plan_state"] not in ("applied", "stale"):
                raise q.RaceError("NOT_APPLIED", "플랜에 반영된 대회가 아닙니다")
            res = {"undone": link.undo(conn, race_id)}
            choice, st = "later", "none"
        elif action == "adapt":
            link.undo(conn, race_id)  # 다시 반영(stale)일 때 이전 배치를 정리
            res = link.apply(conn, race_id, today)
            if not res["n"]:
                raise q.RaceError("NO_ROWS", "바꿀 계획 행이 없습니다. 플랜을 먼저 만드세요", http=409)
            choice, st = "adapt", "applied"
        else:
            if race["plan_state"] == "applied":
                link.undo(conn, race_id)
            res = {}
            choice, st = action, "none"
        conn.execute("UPDATE race_calendar SET adapt_choice=?, plan_state=?, updated_at=datetime('now') WHERE id=?",
                     (choice, st, race_id))
        return api_ok({**_view(conn, q.require(conn, race_id), today), "plan": res})
    return _run(go)


@api_bp.post("/race-calendar/<int:race_id>/restore")
def restore_route(race_id: int):
    body, err = parse_body(_RESTORE, require_json=False)
    if err:
        return err

    def go(conn, today):
        out = state.restore(conn, race_id, today, confirm_past=bool(body.get("confirm_past")),
                            demote_existing_a=bool(body.get("demote_existing_a")), goal_link=body.get("goal_link"))
        return api_ok(_view(conn, out, today) | {"restore": out["restore"]})
    return _run(go)


@api_bp.post("/race-calendar/<int:race_id>/reopen")
def reopen_route(race_id: int):
    body, err = parse_body(_REOPEN, require_json=False)
    if err:
        return err

    def go(conn, today):
        out = state.reopen(conn, race_id, today, demote_existing_a=bool(body.get("demote_existing_a")),
                           goal_link=body.get("goal_link"))
        return api_ok(_view(conn, out, today))
    return _run(go)
