"""`/api/v1/shoes*` + 활동 신발 배정 — 신발 관리 v2(V2-SHOES). 설계 shoes.md §6.

새 비즈니스 로직 없음 — src/services/shoe_{query,service} 를 호출하고 ShoeError 를 봉투로 옮긴다.
쓰기 후 commit 은 이 계층이 한다. 입력은 validation.py 필드로 검증(위반 400 INVALID_PARAM).
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager

from flask import request

from src.services import shoe_query as q
from src.services import shoe_service as svc
from src.services.shoe_status import CATEGORIES
from src.utils.reference_day import reference_today
from src.utils.user_context import db_path

from . import api_bp, api_error, api_ok
from .validation import date_field, enum_field, float_field, int_field, int_list_field, parse_args, parse_body, str_field

_ID = int_field(1, 2**31 - 1)
_FIELDS = {
    "name": str_field(60),
    "brand": str_field(60),
    "model": str_field(60),
    "category": enum_field(CATEGORIES),
    "start_date": date_field(),
    "initial_distance_km": float_field(0, 3000),
    "retire_km": int_field(100, 2000),
    "default_for": enum_field(("road", "trail", "treadmill")),
    "notes": str_field(500),
}
_PATCH = {**_FIELDS, "retired_at": date_field()}
_CREATE = {**_FIELDS, "name": str_field(60, required=True)}
_PAGE = {"cursor": int_field(0, 10**6, default=0), "limit": int_field(1, 100, default=30)}


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


def _run(fn, *, write: bool = True):
    """DB 열기 → fn(conn, today) → commit/rollback → ShoeError 변환."""
    with _conn() as conn:
        if conn is None:
            return api_error("NOT_FOUND", "running.db 없음", 503)
        try:
            out = fn(conn, reference_today(conn)[0])
            if write:
                conn.commit()
            return out
        except svc.ShoeError as exc:
            conn.rollback()
            return api_error(exc.code, str(exc), exc.http)
        except sqlite3.IntegrityError:
            conn.rollback()
            return api_error("CONFLICT", "다른 변경과 충돌했어요. 다시 시도해 주세요.", 409)


def _detail(conn, shoe_id: int, today: str, status: int = 200):
    view = q.get_shoe(conn, shoe_id, today)
    if view is None:
        return api_error("NOT_FOUND", "신발을 찾을 수 없어요", 404)
    return api_ok(view, status)


def _present(clean: dict) -> dict:
    """PATCH — 본문에 실제로 있던 키만(명시적 null 은 '비우기'로 유지)."""
    raw = request.get_json(silent=True) or {}
    return {k: v for k, v in clean.items() if k in raw}


@api_bp.get("/shoes")
def list_shoes():
    include = request.args.get("include_retired", "1") not in ("0", "false")
    return _run(lambda c, t: api_ok(q.list_shoes(c, t, include_retired=include)), write=False)


@api_bp.get("/shoes/alert")
def shoe_alert():
    return _run(lambda c, t: api_ok({"alert": q.today_alert(c, t)}), write=False)


@api_bp.get("/shoes/unassigned")
def unassigned_runs():
    args, err = parse_args(_PAGE)
    if err:
        return err
    return _run(lambda c, t: api_ok(q.unassigned_activities(c, args["cursor"], args["limit"])), write=False)


@api_bp.get("/shoes/<int:shoe_id>")
def get_shoe(shoe_id: int):
    return _run(lambda c, t: _detail(c, shoe_id, t), write=False)


@api_bp.get("/shoes/<int:shoe_id>/activities")
def shoe_activities(shoe_id: int):
    args, err = parse_args(_PAGE)
    if err:
        return err

    def go(c, t):
        if q.require(c, shoe_id) is None:
            return api_error("NOT_FOUND", "신발을 찾을 수 없어요", 404)
        return api_ok(q.shoe_activities(c, shoe_id, args["cursor"], args["limit"]))
    return _run(go, write=False)


@api_bp.post("/shoes")
def create_shoe():
    body, err = parse_body(_CREATE)
    if err:
        return err
    return _run(lambda c, t: _detail(c, svc.create(c, body, t), t, 201))


@api_bp.patch("/shoes/<int:shoe_id>")
def update_shoe(shoe_id: int):
    body, err = parse_body(_PATCH)
    if err:
        return err
    changes = _present(body)

    def go(c, t):
        svc.update(c, shoe_id, changes, t)
        return _detail(c, shoe_id, t)
    return _run(go)


@api_bp.delete("/shoes/<int:shoe_id>")
def delete_shoe(shoe_id: int):
    def go(c, t):
        svc.delete(c, shoe_id)
        return api_ok({"deleted": shoe_id})
    return _run(go)


@api_bp.post("/shoes/<int:shoe_id>/merge")
def merge_shoe(shoe_id: int):
    body, err = parse_body({"source_shoe_id": int_field(1, 2**31 - 1, required=True)})
    if err:
        return err

    def go(c, t):
        svc.merge(c, shoe_id, body["source_shoe_id"])
        return _detail(c, shoe_id, t)
    return _run(go)


@api_bp.post("/shoes/<int:shoe_id>/gear")
def link_gear(shoe_id: int):
    body, err = parse_body({"gear_id": int_field(1, 2**31 - 1, required=True)})
    if err:
        return err

    def go(c, t):
        svc.link_gear(c, shoe_id, body["gear_id"])
        return _detail(c, shoe_id, t)
    return _run(go)


@api_bp.delete("/shoes/<int:shoe_id>/gear/<int:gear_id>")
def unlink_gear(shoe_id: int, gear_id: int):
    def go(c, t):
        svc.unlink_gear(c, shoe_id, gear_id)
        return _detail(c, shoe_id, t)
    return _run(go)


@api_bp.post("/shoes/import-gear")
def import_gear():
    return _run(lambda c, t: api_ok(svc.import_gear(c, t)))


@api_bp.post("/shoes/<int:shoe_id>/assign")
def assign_bulk(shoe_id: int):
    body, err = parse_body({"activity_ids": int_list_field(max_items=200, required=True)})
    if err:
        return err
    return _run(lambda c, t: api_ok(svc.assign_bulk(c, shoe_id, body["activity_ids"])))


@api_bp.put("/library/activities/<int:activity_id>/shoe")
def put_activity_shoe(activity_id: int):
    body, err = parse_body({"shoe_id": _ID})
    if err:
        return err
    raw = request.get_json(silent=True) or {}
    if "shoe_id" not in raw:
        return api_error("INVALID_PARAM", "요청 값이 올바르지 않습니다.", 400, {"shoe_id": "필수 항목입니다"})

    def go(c, t):
        svc.set_activity_shoe(c, activity_id, body["shoe_id"])
        return api_ok({"shoe": q.activity_shoe_view(c, activity_id)})
    return _run(go)


@api_bp.delete("/library/activities/<int:activity_id>/shoe")
def delete_activity_shoe(activity_id: int):
    def go(c, t):
        svc.clear_activity_shoe(c, activity_id)
        return api_ok({"shoe": q.activity_shoe_view(c, activity_id)})
    return _run(go)
