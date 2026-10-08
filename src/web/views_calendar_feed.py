"""캘린더 구독 공개 피드 — GET|HEAD /feeds/cal/<token>.ics (토큰 인증, 세션·쿠키 없음).

설계: v0.3/data/phase-7-ui-renewal/ux-review-2026-09/DESIGN-ICS-SUBSCRIBE.md §4
"""
from __future__ import annotations

import hashlib
import logging
import sqlite3

from flask import Blueprint, Response, request

from src.db_setup import get_db_path
from src.services import calendar_feed_index as feeds
from src.services.calendar_feed_service import build_ics, default_range
from src.utils import rate_window

log = logging.getLogger(__name__)
calendar_feed_bp = Blueprint("calendar_feed", __name__)

_TOKEN_LIMIT = (60, 3600)
_IP_404_LIMIT = (20, 600)


def client_family(ua: str) -> str:
    u = (ua or "").lower()
    if "google" in u or "calendar-importer" in u:
        return "google"
    if any(k in u for k in ("ios", "macos", "dataaccessd", "calendaragent", "iphone", "mac os")):
        return "apple"
    if "outlook" in u or "microsoft" in u:
        return "outlook"
    return "other"


def _ip() -> str:
    return (request.headers.get("CF-Connecting-IP") or request.remote_addr or "?").strip()


def _not_found() -> Response:
    resp = Response("Not Found", status=404, mimetype="text/plain")
    resp.headers["Cache-Control"] = "no-store"
    resp.headers["X-Robots-Tag"] = "noindex, nofollow"
    return resp


def _miss() -> Response:
    ip_key = f"ip404:{_ip()}"
    if rate_window.count(ip_key, _IP_404_LIMIT[1]) >= _IP_404_LIMIT[0]:
        return Response("Too Many Requests", status=429, headers={"Retry-After": "600"})
    rate_window.hit(ip_key, *_IP_404_LIMIT)
    return _not_found()


@calendar_feed_bp.route("/feeds/cal/<token>.ics", methods=["GET", "HEAD"])
def calendar_feed(token: str) -> Response:
    found = feeds.lookup(token)
    if not found:
        return _miss()
    uid, token_hash = found
    if not rate_window.hit(f"tok:{token_hash}", *_TOKEN_LIMIT):
        return Response("Too Many Requests", status=429, headers={"Retry-After": "600"})
    db = get_db_path(uid, create=False)
    if not db.exists():
        return _not_found()
    try:
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=10)
        try:
            frm, to = default_range(conn)
            body = build_ics(conn, frm, to, uid_salt=token_hash)
        finally:
            conn.close()
    except Exception:
        log.exception("[calendar_feed] 피드 생성 실패")
        return Response("Service Unavailable", status=503, headers={"Retry-After": "600"})
    try:
        feeds.touch(token_hash, client_family(request.headers.get("User-Agent", "")))
    except Exception:
        log.warning("[calendar_feed] touch 실패", exc_info=True)

    etag = '"' + hashlib.sha256(body.encode("utf-8")).hexdigest()[:32] + '"'
    headers = {"ETag": etag, "Cache-Control": "private, no-cache",
               "X-Robots-Tag": "noindex, nofollow"}
    if etag in request.headers.get("If-None-Match", ""):
        return Response(status=304, headers=headers)
    resp = Response(body if request.method == "GET" else b"",
                    mimetype="text/calendar", headers=headers)
    resp.headers["Content-Type"] = "text/calendar; charset=utf-8"
    return resp
