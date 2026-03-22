"""활동 그룹 병합/분리 API — Flask Blueprint.

POST /activities/merge   body: {"ids": [1, 2, 3]}
POST /activities/ungroup body: {"id": 5}
"""
from __future__ import annotations

import json
import sqlite3

from flask import Blueprint, Response, request

from .helpers import db_path
from src.services.unified_activities import (
    assign_group_to_activities,
    remove_from_group,
)
from src.utils.dedup import auto_group_all

merge_bp = Blueprint("activity_merge", __name__)


def _json_response(data: dict, status: int = 200) -> Response:
    return Response(json.dumps(data, ensure_ascii=False), status=status, mimetype="application/json")


@merge_bp.post("/activities/merge")
def activities_merge():
    """2개 이상 활동을 하나의 그룹으로 묶기."""
    body = request.get_json(silent=True) or {}
    raw_ids = body.get("ids", [])
    if not isinstance(raw_ids, list) or len(raw_ids) < 2:
        return _json_response({"ok": False, "error": "ids는 2개 이상 정수 배열이어야 합니다."}, 400)

    try:
        ids = [int(i) for i in raw_ids]
    except (TypeError, ValueError):
        return _json_response({"ok": False, "error": "ids에 유효하지 않은 값이 있습니다."}, 400)

    dpath = db_path()
    if not dpath.exists():
        return _json_response({"ok": False, "error": "running.db 없음"}, 500)

    try:
        with sqlite3.connect(str(dpath)) as conn:
            group_id = assign_group_to_activities(conn, ids)
    except Exception as exc:
        return _json_response({"ok": False, "error": str(exc)}, 500)

    return _json_response({"ok": True, "group_id": group_id})


@merge_bp.post("/activities/ungroup")
def activities_ungroup():
    """활동 하나를 그룹에서 분리."""
    body = request.get_json(silent=True) or {}
    raw_id = body.get("id")
    if raw_id is None:
        return _json_response({"ok": False, "error": "id가 필요합니다."}, 400)

    try:
        activity_id = int(raw_id)
    except (TypeError, ValueError):
        return _json_response({"ok": False, "error": "id가 유효하지 않습니다."}, 400)

    dpath = db_path()
    if not dpath.exists():
        return _json_response({"ok": False, "error": "running.db 없음"}, 500)

    try:
        with sqlite3.connect(str(dpath)) as conn:
            remove_from_group(conn, activity_id)
    except Exception as exc:
        return _json_response({"ok": False, "error": str(exc)}, 500)

    return _json_response({"ok": True})


@merge_bp.post("/activities/auto-group")
def activities_auto_group():
    """모든 활동에 대해 cross-source 중복 자동 묶기."""
    dpath = db_path()
    if not dpath.exists():
        return _json_response({"ok": False, "error": "running.db 없음"}, 500)

    try:
        with sqlite3.connect(str(dpath)) as conn:
            result = auto_group_all(conn)
    except Exception as exc:
        return _json_response({"ok": False, "error": str(exc)}, 500)

    return _json_response({"ok": True, **result})
