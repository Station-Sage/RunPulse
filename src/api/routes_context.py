"""`/api/context-episodes*` — 질병·여행·고도 컨텍스트 에피소드와 AI 동의 (NEW-40, ADR-035 v3).

`/api/v1` 밖의 별도 블루프린트이며 오류는 같은 봉투(`register_envelope_handlers`)로 나간다.
쓰기 요청은 Origin 관문을 그대로 거친다(면제 경로 아님).
"""
from __future__ import annotations

import sqlite3

from flask import Blueprint

from src.services import context_autodetect as autodetect
from src.services import context_episodes as eps
from src.services import illness_consent as consent
from src.services import input_limits as lim
from src.services.context_episode_delete import delete_episode
from src.utils.user_context import db_path

from . import api_error, api_ok, register_envelope_handlers
from .validation import (date_field, dict_field, enum_field, int_field, int_list_field, parse_args, parse_body,
                         str_field)

context_bp = Blueprint("context_episodes", __name__, url_prefix="/api/context-episodes")
register_envelope_handlers(context_bp)

_DETAIL = dict_field({
    "site": str_field(lim.CONTEXT_SITE_MAX),
    "delta_h": int_field(*lim.CONTEXT_TRAVEL_DELTA_H),
    "direction": enum_field(("east", "west")),
    "altitude_m": int_field(*lim.CONTEXT_ALTITUDE_M),
    "band": str_field(16),
})
_CREATE = {
    "kind": enum_field(eps.KINDS, required=True),
    "start_date": date_field(),
    "severity": int_field(*lim.CONTEXT_EPISODE_SEVERITY),
    "detail": _DETAIL,
}


def _open() -> sqlite3.Connection | None:
    p = db_path()
    return sqlite3.connect(str(p)) if p.exists() else None


def _no_db():
    return api_error("NOT_FOUND", "running.db 없음", 503)


def _state(conn) -> dict:
    return {"episodes": eps.list_all(conn), "illness_reconfirm": eps.illness_reconfirm(conn),
            "consent": {"action": consent.current_action(conn), "needs_first_prompt": consent.needs_first_prompt(conn)}}


@context_bp.get("")
def list_episodes():
    args, err = parse_args({"include_dismissed": enum_field(("0", "1"), default="0")})
    if err:
        return err
    conn = _open()
    if conn is None:
        return _no_db()
    try:
        eps.expire_candidates(conn)
        detected = autodetect.run(conn)
        conn.commit()
        out = _state(conn)
        out["health_question"] = detected["health_question"]
        if args["include_dismissed"] == "1":
            out["episodes"] = eps.list_all(conn, include_dismissed=True)
        return api_ok(out)
    finally:
        conn.close()


@context_bp.post("")
def create_episode():
    body, err = parse_body(_CREATE)
    if err:
        return err
    conn = _open()
    if conn is None:
        return _no_db()
    try:
        first = body["kind"] == "illness" and consent.needs_first_prompt(conn)
        sev = body.get("severity") if body["kind"] == "illness" else None
        eid = eps.open_episode(conn, body["kind"], start_date=body.get("start_date"), severity=sev,
                               detail=body.get("detail"))
        conn.commit()
        row = next(e for e in eps.list_all(conn) if e["id"] == eid)
        return api_ok({"episode": row, "needs_consent_prompt": first}, 201)
    finally:
        conn.close()


def _transition(episode_id: int, fn, **kw):
    conn = _open()
    if conn is None:
        return _no_db()
    try:
        if not fn(conn, episode_id, **kw):
            return api_error("CONFLICT", "처리할 수 없는 상태입니다.", 409)
        conn.commit()
        return api_ok({"episode": next(e for e in eps.list_all(conn, include_dismissed=True) if e["id"] == episode_id)})
    finally:
        conn.close()


@context_bp.post("/<int:episode_id>/confirm")
def confirm_episode(episode_id: int):
    return _transition(episode_id, eps.confirm)


@context_bp.post("/<int:episode_id>/dismiss")
def dismiss_episode(episode_id: int):
    return _transition(episode_id, eps.dismiss)


@context_bp.post("/<int:episode_id>/close")
def close_episode(episode_id: int):
    body, err = parse_body({"end_date": date_field()}, require_json=False)
    if err:
        return err
    return _transition(episode_id, eps.close, end_date=body.get("end_date"))


@context_bp.delete("/<int:episode_id>")
def remove_episode(episode_id: int):
    body, err = parse_body({"chat_thread_ids": int_list_field(max_items=lim.CONTEXT_CHAT_THREADS_MAX, default=[])},
                           require_json=False)
    if err:
        return err
    conn = _open()
    if conn is None:
        return _no_db()
    try:
        res = delete_episode(conn, episode_id, chat_thread_ids=body.get("chat_thread_ids") or [])
        if res is None:
            return api_error("NOT_FOUND", "에피소드가 없습니다.", 404)
        conn.commit()
        return api_ok(res)
    finally:
        conn.close()


@context_bp.get("/consent")
def get_consent():
    conn = _open()
    if conn is None:
        return _no_db()
    try:
        return api_ok({"action": consent.current_action(conn), "needs_first_prompt": consent.needs_first_prompt(conn)})
    finally:
        conn.close()


@context_bp.post("/consent")
def post_consent():
    body, err = parse_body({"action": enum_field(("grant", "decline", "revoke"), required=True),
                            "via": enum_field(("first_input", "settings"), required=True)})
    if err:
        return err
    conn = _open()
    if conn is None:
        return _no_db()
    try:
        consent.record(conn, body["action"], body["via"])
        conn.commit()
        return api_ok({"action": consent.current_action(conn)}, 201)
    finally:
        conn.close()
