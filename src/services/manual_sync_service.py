"""수동 동기화 1소스 실행 — 원장 선점(claim_run) → sync.py subprocess → 원장 판독으로 결과 dict 생성."""
from __future__ import annotations

import logging
import subprocess
import sys
import uuid
from datetime import date, timedelta
from pathlib import Path

from src.sync.ledger import claim_run, fail_run
from src.utils.sync_jobs import get_job

log = logging.getLogger(__name__)

TIMEOUT_SEC = 300
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def skipped(src: str, error: str, reason: str | None = None, **extra) -> dict:
    r = {"source": src, "ok": False, "skipped": True, "count": 0, "error": error}
    if reason:
        r["reason"] = reason
    r.update({k: v for k, v in extra.items() if v is not None})
    return r


def precheck(src: str, user_id: str, hist_days: int | None, days_default: int):
    """재시도 대기·정책 검사. (days, guard, 건너뜀 결과 또는 None)."""
    from src.utils.sync_gates import wait_sec
    from src.utils.sync_ledger_query import last_success_at
    from src.utils.sync_policy import _fmt_duration, check_incremental_guard, check_range_guard

    retry_sec = wait_sec(src, user_id)
    if retry_sec and retry_sec > 0:
        return None, None, skipped(
            src, f"{src} — {_fmt_duration(retry_sec)} 후 재시도 가능합니다.",
            "retry_after", retry_after_sec=retry_sec)
    if hist_days is not None:
        guard, days = check_range_guard(src, hist_days), hist_days
    else:
        guard, days = check_incremental_guard(src, last_success_at(src, user_id)), days_default
    if not guard.allowed:
        return None, guard, skipped(
            src, guard.message_ko or "정책 제한", guard.reason, retry_after_sec=guard.retry_after_sec)
    return days, guard, None


def run_one(src: str, days: int, user_id: str, warn: str | None = None) -> dict:
    """원장 선점 후 subprocess 로 동기화. 선점 실패면 'running' 건너뜀 결과."""
    today = date.today()
    job_id = claim_run(
        src, (today - timedelta(days=days)).isoformat(), today.isoformat(),
        source_path="manual", job_id=str(uuid.uuid4()), user_id=user_id,
    )
    if job_id is None:
        return skipped(src, f"{src} 동기화가 이미 진행 중입니다. 잠시 후 다시 시도하세요.", "running")
    try:
        proc = subprocess.run(
            [sys.executable, "src/sync.py", "--source", src, "--days", str(days),
             "--user", user_id, "--job-id", job_id, "--trigger", "manual"],
            capture_output=True, text=True, timeout=TIMEOUT_SEC, cwd=str(PROJECT_ROOT),
        )
    except subprocess.TimeoutExpired:
        log.error("[manual_sync] %s 타임아웃", src)
        fail_run(job_id, "timeout", f"타임아웃 ({TIMEOUT_SEC}초)", service=src)
        return {"source": src, "ok": False, "skipped": False, "count": 0,
                "error": f"동기화 타임아웃 ({TIMEOUT_SEC}초 초과)"}
    except Exception as e:
        log.error("[manual_sync] %s 예외: %s", src, e, exc_info=True)
        fail_run(job_id, "unknown", str(e), service=src)
        return {"source": src, "ok": False, "skipped": False, "count": 0, "error": str(e)}

    for line in (proc.stdout or "").splitlines():
        log.info("[sync.py stdout] %s", line)
    for line in (proc.stderr or "").splitlines():
        log.warning("[sync.py stderr] %s", line)
    stderr_tail = (proc.stderr or "")[-400:]
    if proc.returncode != 0:
        fail_run(job_id, "unknown", stderr_tail, service=src)
        return {"source": src, "ok": False, "skipped": False, "count": 0,
                "error": stderr_tail, "warn": warn}
    job = get_job(job_id)
    if job is not None and job.status == "failed":
        return {"source": src, "ok": False, "skipped": False, "count": 0,
                "error": job.last_error or job.error_code or "동기화 실패", "warn": warn}
    count = job.synced_count if job else 0
    partial = bool(job and job.error_code == "partial_rate_limited")
    return {"source": src, "ok": count > 0 or not partial, "skipped": False,
            "count": count, "partial": partial, "warn": warn}
