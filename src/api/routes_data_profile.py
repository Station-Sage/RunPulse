"""`/api/v1/data/profile*` — 러너 기준값 조회·미리보기·저장 (routes_data 에서 분리, D-07·D-08 상태 검사)."""
from __future__ import annotations

import sqlite3

from flask import request

from src.services import profile_service
from src.utils.config import load_config
from src.utils.user_context import db_path, get_current_user_id

from . import api_bp, api_error, api_ok

_STATUS = {"SOURCE_UNAVAILABLE": 422, "INVALID_PARAM": 400}


def _with_conn(fn):
    """running.db 읽기 커넥션 + 설정을 넘겨 호출. DB가 없으면 503."""
    dpath = db_path()
    if not dpath.exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)
    config = load_config(user_id=get_current_user_id())
    conn = sqlite3.connect(str(dpath))
    try:
        return fn(conn, config)
    finally:
        conn.close()


@api_bp.get("/data/profile")
def get_data_profile():
    return _with_conn(lambda c, cfg: api_ok({"rows": profile_service.profile_rows(c, cfg)}))


@api_bp.post("/data/profile/preview")
def preview_data_profile():
    from src.services import recompute_service

    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return api_error("INVALID_PARAM", "JSON 본문이 필요해요")
    changes, err = profile_service.validate_changes(body.get("changes") if isinstance(body.get("changes"), dict) else body)
    if err:
        return api_error("INVALID_PARAM", err)
    return _with_conn(lambda c, cfg: api_ok(recompute_service.preview_profile(c, cfg, changes)))


@api_bp.patch("/data/profile")
def patch_data_profile():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return api_error("INVALID_PARAM", "JSON 본문이 필요해요")
    mode = body.get("recompute", "none")
    if mode not in ("none", "90d"):
        return api_error("INVALID_PARAM", "recompute는 none 또는 90d예요")
    changes, err = profile_service.validate_changes(body)
    if err:
        return api_error("INVALID_PARAM", err)
    if not db_path().exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)
    user_id = get_current_user_id()
    config = load_config(user_id=user_id)
    conn = sqlite3.connect(str(db_path()))
    try:
        bad = profile_service.check_changes(conn, config, changes)
    finally:
        conn.close()
    if bad:
        return api_error(bad[0], bad[1], _STATUS[bad[0]])
    config = profile_service.apply_changes(config, user_id, changes)
    job_id = None
    if mode == "90d":
        from src.services import recompute_service

        data, _code = recompute_service.start(user_id, "90d", None, "profile")
        job_id = (data or {}).get("job_id")
    return _with_conn(lambda c, _cfg: api_ok({"rows": profile_service.profile_rows(c, config), "job_id": job_id}))
