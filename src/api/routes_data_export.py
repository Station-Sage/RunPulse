"""`/api/v1/data/export*` — 빠른 CSV 스트림, 아카이브 작업, 내보내기 이력/다운로드. design §2.4·§7.2."""
from __future__ import annotations

import sqlite3

from flask import Response, request, send_file

from src.services import export_service
from src.web.helpers import db_path, get_current_user_id

from . import api_bp, api_error, api_ok


@api_bp.post("/data/export")
def post_data_export():
    body = request.get_json(silent=True)
    params, err = export_service.parse_params(body if isinstance(body, dict) else {})
    if err:
        return api_error("INVALID_PARAM", err)
    dpath = db_path()
    if not dpath.exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)
    if params["kind"] == "archive":
        data, code = export_service.start_archive(get_current_user_id(), params["from"], params["to"])
        if code:
            return api_error(code, "이미 아카이브를 만드는 중이에요", 409, data)
        return api_ok(data, 202)
    conn = sqlite3.connect(str(dpath))
    try:
        text = export_service.quick_export(conn, params["kind"], params["from"], params["to"])
    finally:
        conn.close()
    name = export_service.quick_filename(params["kind"])
    return Response(text, mimetype="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{name}"'})


@api_bp.get("/data/exports")
def get_data_exports():
    return api_ok({"exports": export_service.history()})


@api_bp.get("/data/exports/<job_id>/download")
def download_data_export(job_id: str):
    from src.utils.sync_jobs import get_job

    job = get_job(job_id)
    if job is None or job.service != export_service.SERVICE:
        return api_error("NOT_FOUND", "내보내기를 찾을 수 없어요", 404)
    view = export_service.job_view(job)
    if view["state"] == "expired":
        return api_error("EXPIRED", "보관 기간(7일)이 지나 받을 수 없어요. 다시 만들어 주세요", 410)
    path = export_service.exports_dir(get_current_user_id()) / f"{job.id}.zip"
    if view["state"] != "done" or not path.exists():
        return api_error("NOT_FOUND", "파일이 아직 없어요", 404)
    return send_file(path, mimetype="application/zip", as_attachment=True, download_name=view["result"]["filename"])
