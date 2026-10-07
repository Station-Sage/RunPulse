"""`/api/v1/data/*` — 데이터 관리(동기화 상태 등). 40-v2-unimplemented design §7.3."""
from __future__ import annotations

import sqlite3

from flask import request

from src.services import data_service, sync_state_service
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


@api_bp.get("/data/summary")
def get_data_summary():
    return _with_conn(lambda c, cfg: api_ok(data_service.summary(c, cfg)))


@api_bp.get("/data/sources")
def get_data_sources():
    return _with_conn(lambda c, cfg: api_ok({"sources": data_service.sources(c, cfg)}))


@api_bp.get("/data/sources/<provider>")
def get_data_source(provider: str):
    def run(c, cfg):
        detail = data_service.source_detail(c, cfg, provider)
        return api_ok(detail) if detail else api_error("NOT_FOUND", "알 수 없는 소스예요", 404)
    return _with_conn(run)


@api_bp.get("/data/runs")
def get_data_runs():
    provider = request.args.get("provider") or None
    if provider is not None and provider not in _VALID_SOURCES:
        return api_error("INVALID_PARAM", "provider가 올바르지 않아요")
    try:
        limit = int(request.args.get("limit", 20))
    except ValueError:
        return api_error("INVALID_PARAM", "limit이 올바르지 않아요")
    errors_only = request.args.get("errors_only") in ("1", "true")
    return api_ok({"runs": data_service.runs(provider, errors_only, limit)})
