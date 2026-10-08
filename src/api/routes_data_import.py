"""`/api/v1/data/import*` — 업로드+미리보기, 실행 작업, 가져오기 이력. design §2.4 가져오기."""
from __future__ import annotations

from flask import request

from src.services import import_service
from src.utils.sync_jobs import get_job
from src.web.helpers import db_path, get_current_user_id

from . import api_bp, api_error, api_ok


def _source() -> str | None:
    s = (request.values.get("source") or "garmin").strip()
    return s if s in import_service.SOURCES else None


@api_bp.post("/data/import/preview")
def post_data_import_preview():
    source = _source()
    if source is None:
        return api_error("INVALID_PARAM", "source는 garmin 또는 strava예요")
    files = [(f.filename, f) for f in request.files.getlist("files") if f.filename]
    if not files:
        return api_error("INVALID_PARAM", "파일을 선택해 주세요")
    if not db_path().exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)
    uid = get_current_user_id()
    upload_id, paths = import_service.save_upload(uid, files)
    if sum(p.stat().st_size for p in paths) > import_service.MAX_BYTES:
        return api_error("TOO_LARGE", "파일이 너무 커요(최대 500MB)", 413)
    kind, err = import_service.detect_kind(paths)
    if err:
        return api_error("INVALID_UPLOAD", err)
    try:
        data = import_service.preview(uid, kind, paths, source)
    except Exception as e:  # noqa: BLE001
        return api_error("PREVIEW_FAILED", f"미리보기에 실패했어요: {str(e)[:120]}", 500)
    return api_ok({"upload_id": upload_id, **data})


@api_bp.post("/data/import")
def post_data_import():
    body = request.get_json(silent=True)
    body = body if isinstance(body, dict) else {}
    upload_id = str(body.get("upload_id") or "")
    source = body.get("source") or "garmin"
    if not upload_id or source not in import_service.SOURCES:
        return api_error("INVALID_PARAM", "upload_id와 source(garmin|strava)가 필요해요")
    data, code = import_service.start(get_current_user_id(), upload_id, source)
    if code == "IMPORT_RUNNING":
        return api_error(code, "이미 가져오는 중이에요", 409, data)
    if code == "UPLOAD_NOT_FOUND":
        return api_error(code, "업로드한 파일을 찾을 수 없어요. 다시 올려 주세요", 404)
    if code:
        return api_error(code, "지원하지 않는 파일이에요")
    return api_ok(data, 202)


@api_bp.get("/data/imports")
def get_data_imports():
    return api_ok({"imports": import_service.history()})


@api_bp.get("/data/imports/<job_id>")
def get_data_import(job_id: str):
    job = get_job(job_id)
    if job is None or job.service != import_service.SERVICE:
        return api_error("NOT_FOUND", "가져오기 작업을 찾을 수 없어요", 404)
    return api_ok(import_service.job_view(job))
