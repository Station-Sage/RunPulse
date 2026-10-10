"""동기화 원장 기록 진입점 — sync_jobs.db에 실행 1건(manual·auto·cli)을 남긴다. bg 경로는 bg_sync가 직접 기록."""
from __future__ import annotations

import json
import logging
import threading
import uuid
from contextlib import contextmanager
from datetime import date, datetime, timedelta

from src.sync.sync_errors import SyncSourceError
from src.utils.sync_ledger_query import STALE_SEC
from src.utils.sync_jobs import _conn, create_job, get_job, insert_job, update_job

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
    partial_code = partial_code or _gate_partial_code(job_id)
    if partial_code:
        kw["error_code"] = partial_code
    update_job(job_id, **kw)


def _gate_partial_code(job_id: str) -> str | None:
    """이 실행이 직접 세운 게이트가 있으면(한도 초과로 일부만 수집) 부분 실패 코드를 돌려준다."""
    try:
        job = get_job(job_id)
        if job is None:
            return None
        from src.utils.sync_gates import gate
        g = gate(job.service)
        if g is not None and g.job_id == job_id:
            return "partial_rate_limited"
    except Exception:
        log.debug("게이트 부분 실패 판정 실패 job=%s", job_id, exc_info=True)
    return None


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


def claim_run(
    service: str, from_date: str, to_date: str, *, source_path: str,
    params: dict | None = None, job_id: str | None = None, user_id: str | None = None,
) -> str | None:
    """같은 service 의 실행 슬롯을 원자적으로 선점한다. 이미 신선한 실행이 있으면 None.

    BEGIN IMMEDIATE 한 트랜잭션에서 stale(하트비트 STALE_SEC 무갱신) 행을 닫고 → 신선한 행 검사 → 삽입.
    """
    job_id = job_id or str(uuid.uuid4())
    now = datetime.now()
    now_s = now.isoformat(timespec="seconds")
    cutoff = (now - timedelta(seconds=STALE_SEC)).isoformat(timespec="seconds")
    conn = _conn(user_id)
    conn.isolation_level = None
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            "UPDATE sync_jobs SET status='stopped', error_code='stale', updated_at=?, finished_at=? "
            "WHERE service=? AND status IN ('pending','running') AND updated_at < ?",
            (now_s, now_s, service, cutoff),
        )
        if conn.execute(
            "SELECT 1 FROM sync_jobs WHERE service=? AND status IN ('pending','running') LIMIT 1",
            (service,),
        ).fetchone():
            conn.execute("ROLLBACK")
            return None
        conn.execute(
            "UPDATE sync_jobs SET status='stopped', updated_at=? "
            "WHERE service=? AND status IN ('paused','stopped','rate_limited')",
            (now_s, service),
        )
        insert_job(
            conn, job_id, service, from_date, to_date, source_path=source_path, status="running",
            params_json=json.dumps(params, ensure_ascii=False) if params else None, now=now_s,
        )
        conn.execute("COMMIT")
        return job_id
    except Exception:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()


@contextmanager
def heartbeat(job_id: str, every_sec: int = 60, user_id: str | None = None):
    """데몬 스레드가 every_sec 마다 updated_at 만 갱신한다. with 종료 시 정지."""
    from src.utils.user_context import resolve_user_id
    uid = resolve_user_id(user_id)
    stop = threading.Event()

    def _beat() -> None:
        while not stop.wait(every_sec):
            try:
                conn = _conn(uid)
                try:
                    with conn:
                        conn.execute(
                            "UPDATE sync_jobs SET updated_at=? WHERE id=? AND status IN ('pending','running')",
                            (datetime.now().isoformat(timespec="seconds"), job_id),
                        )
                finally:
                    conn.close()
            except Exception:
                log.debug("heartbeat 실패 job=%s", job_id, exc_info=True)

    t = threading.Thread(target=_beat, daemon=True, name=f"hb-{job_id[:8]}")
    t.start()
    try:
        yield
    finally:
        stop.set()
