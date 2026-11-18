"""`/api/v1/insights*` — 능동 인사이트 사건 조회·확인·닫기 (V2-REPAIR D2).

조회는 저장된 사건만 읽는다(재계산 없음). 쓰기는 Origin 관문 대상.
"""
from __future__ import annotations

import sqlite3

from src.services import insight_service as svc
from src.utils.user_context import db_path

from . import api_bp, api_error, api_ok
from .validation import enum_field, int_field, parse_args

_ARGS = {"state": enum_field(("open", "all"), default="open"), "limit": int_field(1, 50, default=20)}


def _with_conn(fn):
    dpath = db_path()
    if not dpath.exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)
    conn = sqlite3.connect(str(dpath))
    try:
        return fn(conn)
    finally:
        conn.close()


@api_bp.get("/insights")
def get_insights():
    args, err = parse_args(_ARGS)
    if err:
        return err
    return _with_conn(lambda c: api_ok({"events": svc.list_events(c, args["state"], args["limit"])}))


def _transition(event_id: int, action):
    def run(conn):
        if not action(conn, event_id):
            return api_error("NOT_FOUND", "열린 사건이 아닙니다", 404)
        return api_ok({"id": event_id})
    return _with_conn(run)


@api_bp.post("/insights/<int:event_id>/dismiss")
def post_insight_dismiss(event_id: int):
    return _transition(event_id, svc.dismiss)


@api_bp.post("/insights/<int:event_id>/seen")
def post_insight_seen(event_id: int):
    return _transition(event_id, svc.mark_seen)
