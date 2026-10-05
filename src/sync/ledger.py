"""동기화 원장 기록 진입점 — sync_jobs.db에 실행 1건(manual·auto·cli)을 남긴다. bg 경로는 bg_sync가 직접 기록."""
from __future__ import annotations

import logging
import uuid
from datetime import date, timedelta

from src.sync.sync_errors import SyncSourceError
from src.utils.sync_jobs import create_job, get_job, update_job

log = logging.getLogger(__name__)

SOURCE_PATHS = ("manual", "bg", "auto", "cli")


def start_run(
    service: str, from_date: str | None = None, to_date: str | None = None,
    *, source_path: str, job_id: str | None = None, days: int = 7,
) -> str:
    """원장에 running 행을 만든다. 같은 id가 이미 있으면 재사용한다."""
    job_id = job_id or str(uuid.uuid4())
    if get_job(job_id) is None:
        to = to_date or date.today().isoformat()
        frm = from_date or (date.today() - timedelta(days=days)).isoformat()
        create_job(service, frm, to, source_path=source_path, job_id=job_id)
    update_job(job_id, status="running")
    return job_id


def finish_run(
    job_id: str, *, synced: int = 0,
    error: SyncSourceError | None = None, partial_code: str | None = None,
) -> None:
    """실행 종료 기록. error가 있으면 failed, 없으면 completed(+부분 실패 코드)."""
    if error is not None:
        update_job(
            job_id, status="failed", synced_count=synced, error_code=error.code,
            http_status=error.http_status, last_error=str(error)[:300],
        )
        return
    kw: dict = {"status": "completed", "synced_count": synced}
    if partial_code:
        kw["error_code"] = partial_code
    update_job(job_id, **kw)


def fail_run(
    job_id: str, code: str, message: str, http_status: int | None = None,
    *, service: str = "unknown", source_path: str = "manual",
) -> None:
    """부모 프로세스용 실패 기록. 이미 failed인 행은 덮어쓰지 않고, 행이 없으면 만든다."""
    job = get_job(job_id)
    if job is None:
        start_run(service, source_path=source_path, job_id=job_id)
    elif job.status == "failed":
        return
    update_job(job_id, status="failed", error_code=code,
               http_status=http_status, last_error=message[:300])
