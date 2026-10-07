"""`/api/v1/data/*` — 데이터 관리(동기화 상태 등). 40-v2-unimplemented design §7.3."""
from __future__ import annotations

import sqlite3

from flask import request

from src.services import sync_state_service
from src.utils.config import load_config
from src.web.helpers import db_path, get_current_user_id

from . import api_bp, api_error, api_ok


@api_bp.get("/data/sync-state")
def get_sync_state():
    dpath = db_path()
    if not dpath.exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)
    config = load_config(user_id=get_current_user_id())
    conn = sqlite3.connect(str(dpath))
    try:
        return api_ok(sync_state_service.get_sync_state(conn, config))
    finally:
        conn.close()


_VALID_SOURCES = ("garmin", "strava", "intervals", "runalyze")


@api_bp.post("/data/sync")
def post_data_sync():
    """증분 동기화 시작. 진행 상황은 GET /data/sync-state로 확인."""
    from src.services.sync_trigger_service import trigger_incremental

    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        body = {}
    if body.get("mode", "incremental") != "incremental":
        return api_error("INVALID_PARAM", "mode는 incremental만 지원해요")
    sources = body.get("sources")
    if sources is not None:
        if not isinstance(sources, list) or not sources or any(s not in _VALID_SOURCES for s in sources):
            return api_error("INVALID_PARAM", "sources가 올바르지 않아요")
    if not db_path().exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)

    user_id = get_current_user_id()
    config = load_config(user_id=user_id)
    res = trigger_incremental(config, user_id, sources, source_path="v2")
    skipped = [s.to_dict() for s in res.skipped]
    if res.runs:
        return api_ok({"runs": res.runs, "skipped": skipped}, 202)
    codes = {s.code for s in res.skipped}
    if codes <= {"not_connected", "disabled"}:
        return api_error("NO_SOURCES", "동기화할 수 있는 소스가 없어요", 422, {"skipped": skipped})
    if codes == {"running"}:
        return api_error("SYNC_RUNNING", "이미 동기화 중이에요", 409, {"runs": skipped})
    waits = [s.retry_after_sec or 0 for s in res.skipped if s.code in ("cooldown", "rate_limited")]
    if waits:
        wait = max(1, min((w for w in waits if w), default=1))
        resp, status = api_error("SYNC_COOLDOWN", "잠시 후 다시 시도해 주세요", 429,
                                 {"retry_after_sec": wait, "skipped": skipped})
        resp.headers["Retry-After"] = str(wait)
        return resp, status
    return api_error("SYNC_START_FAILED", "동기화를 시작하지 못했어요", 500, {"skipped": skipped})


_TERMINAL = ("completed", "stopped", "failed")


@api_bp.post("/data/sync/runs/<run_id>/cancel")
def cancel_sync_run(run_id: str):
    """진행 중인 동기화 중지 요청. 이미 끝난 작업이면 현재 상태를 그대로 돌려준다(멱등)."""
    from src.utils.sync_jobs import get_job
    from src.web.bg_sync import stop_job

    job = get_job(run_id)
    if job is None:
        return api_error("NOT_FOUND", "동기화 작업을 찾을 수 없어요", 404)
    if job.status in _TERMINAL:
        return api_ok({"id": job.id, "provider": job.service, "state": job.status, "requested": False})
    stop_job(job.service, get_current_user_id())
    return api_ok({"id": job.id, "provider": job.service, "state": "stopping", "requested": True}, 202)
