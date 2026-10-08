"""`/api/v1/data/calendar-feed` — 캘린더 구독 주소 조회/발급·재발급/해제. design ICS-SUBSCRIBE §6."""
from __future__ import annotations

from flask import request

from src.services import calendar_feed_index as feeds
from src.utils.public_url import public_base_url
from src.web.helpers import get_current_user_id

from . import api_bp, api_error, api_ok

CONTENTS = ["날짜·종류·거리", "목표 페이스·심박 존", "인터벌 구성"]
EXCLUDED = ["메모·AI 설명", "심박 수치·웰니스", "완료 여부", "대회명·장소"]


def _view(st: dict | None) -> dict:
    base = {"enabled": st is not None, "refresh_hint_hours": 6,
            "contents": CONTENTS, "excluded": EXCLUDED}
    if st is None:
        return base
    token = st["token"]
    url = f"{public_base_url()}/feeds/cal/{token}.ics" if token else None
    return {**base, "url": url,
            "webcal_url": ("webcal://" + url.split("://", 1)[1]) if url else None,
            "revealable": token is not None, "created_at": st["created_at"],
            "last_access_at": st["last_access_at"], "last_client": st["last_client"]}


def _no_store(resp):
    body, status = resp
    body.headers["Cache-Control"] = "no-store"
    return body, status


@api_bp.get("/data/calendar-feed")
def get_data_calendar_feed():
    return _no_store(api_ok(_view(feeds.get_status(get_current_user_id()))))


@api_bp.post("/data/calendar-feed")
def post_data_calendar_feed():
    uid = get_current_user_id()
    rotate = bool((request.get_json(silent=True) or {}).get("rotate"))
    if feeds.get_status(uid) is not None and not rotate:
        return _no_store(api_error("FEED_EXISTS", "이미 구독 주소가 있어요", 409))
    feeds.issue(uid)
    return _no_store(api_ok(_view(feeds.get_status(uid)), 201))


@api_bp.delete("/data/calendar-feed")
def delete_data_calendar_feed():
    feeds.revoke(get_current_user_id())
    from flask import Response
    return Response(status=204, headers={"Cache-Control": "no-store"})
