"""백그라운드 기간 동기화 실행기 — 서비스별 Thread + pause/stop 제어.

특징:
- Garmin 클라이언트 재사용 (배치 간 재인증 없음)
- pause_event / stop_event 로 활동 단위 중단 가능
- rate_limit 자동 대기 후 재개
- sync_jobs 테이블로 진행 상태 추적
"""
from __future__ import annotations

import sqlite3
import threading
import time
from datetime import date, datetime, timedelta
from typing import Optional

from src.db_setup import get_db_path
from src.utils.sync_jobs import (
    SyncJob,
    INTER_BATCH_SLEEP,
    cleanup_stale_running_jobs,
    create_job,
    get_active_job,
    get_job,
    update_job,
    windows,
)
from src.utils.sync_state import get_retry_after_sec

# ── 전역 스레드 레지스트리 ────────────────────────────────────────────────
_threads: dict[str, "BgSyncThread"] = {}
_lock = threading.Lock()

# 프로세스 시작 시 이전 실행에서 남은 stale "running" 작업 정리
try:
    _cleaned = cleanup_stale_running_jobs()
    if _cleaned:
        print(f"[bg_sync] stale 작업 {_cleaned}개 정리됨")
except Exception:
    pass


# ── 스레드 ───────────────────────────────────────────────────────────────

class BgSyncThread(threading.Thread):
    """서비스별 백그라운드 동기화 스레드."""

    def __init__(self, job_id: str, config: dict) -> None:
        super().__init__(daemon=True, name=f"bgsync-{job_id[:8]}")
        self.job_id = job_id
        self.config = config
        self._pause_event = threading.Event()
        self._stop_event = threading.Event()
        self._pause_event.set()   # 기본: 실행 상태

    def pause(self) -> None:
        self._pause_event.clear()

    def resume(self) -> None:
        self._pause_event.set()

    def stop(self) -> None:
        self._stop_event.set()
        self._pause_event.set()   # 일시정지 해제 → 루프 종료 진행

    def run(self) -> None:
        job = get_job(self.job_id)
        if job is None:
            return
        update_job(self.job_id, status="running")
        try:
            self._run_batches(job)
        except Exception as exc:
            update_job(self.job_id, status="stopped", last_error=str(exc)[:300])
        finally:
            with _lock:
                _threads.pop(job.service, None)

    # ── 배치 루프 ─────────────────────────────────────────────────────

    def _run_batches(self, job: SyncJob) -> None:
        all_windows = windows(job.from_date, job.to_date, job.window_days)
        current_from = job.current_from or job.from_date
        pending = [(f, t) for f, t in all_windows if f >= current_from]

        # Garmin 클라이언트 한 번만 로그인
        garmin_client = None
        if job.service == "garmin":
            garmin_client = self._garmin_login()
            if garmin_client is None:
                update_job(self.job_id, status="stopped", last_error="Garmin 로그인 실패")
                return

        total_synced = job.synced_count
        total_req = job.req_count

        for win_from, win_to in pending:
            # 1) 중지 확인
            if self._stop_event.is_set():
                update_job(self.job_id, status="paused", current_from=win_from)
                return

            # 2) 일시정지 대기
            if not self._pause_event.is_set():
                update_job(self.job_id, status="paused")
                self._pause_event.wait()
                if self._stop_event.is_set():
                    update_job(self.job_id, status="paused", current_from=win_from)
                    return

            update_job(self.job_id, status="running", current_from=win_from)

            # 3) rate limit 대기
            retry_sec = get_retry_after_sec(job.service)
            if retry_sec and retry_sec > 0:
                reset_at = (
                    datetime.now() + timedelta(seconds=retry_sec)
                ).isoformat(timespec="seconds")
                update_job(
                    self.job_id,
                    status="rate_limited",
                    retry_after=reset_at,
                    last_error=f"API 한도 도달 — {retry_sec}초 후 재개",
                )
                self._interruptible_sleep(float(retry_sec))
                if self._stop_event.is_set():
                    update_job(self.job_id, status="paused", current_from=win_from)
                    return
                update_job(
                    self.job_id, status="running",
                    retry_after=None, last_error=None,
                )

            # 4) 배치 실행
            count, req_added = self._run_one_batch(
                job.service, win_from, win_to, garmin_client
            )
            total_synced += count
            total_req += req_added

            # 5) 진행 업데이트
            completed = (
                date.fromisoformat(win_to) - date.fromisoformat(job.from_date)
            ).days + 1
            update_job(
                self.job_id,
                completed_days=completed,
                synced_count=total_synced,
                req_count=total_req,
            )

            # 6) 배치 간 대기
            self._interruptible_sleep(INTER_BATCH_SLEEP.get(job.service, 3.0))

        update_job(self.job_id, status="completed")

        # 동기화 완료 후 메트릭 자동 재계산 + 재동기화 플래그 해제
        try:
            import sqlite3 as _sqlite3
            from src.metrics import engine as metrics_engine
            from datetime import date as _date
            with _sqlite3.connect(str(get_db_path()), timeout=30) as conn:
                conn.execute("PRAGMA journal_mode=WAL")
                # 오늘 날짜를 항상 포함하여 메트릭 계산
                end = max(job.to_date, _date.today().isoformat())
                metrics_engine.run_for_date_range(conn, job.from_date, end)
                # 스키마 마이그레이션 후 재동기화 플래그 해제
                from src.db_setup import clear_needs_resync
                clear_needs_resync(conn)
                conn.commit()
        except Exception as exc:
            update_job(self.job_id, last_error=f"메트릭 계산 실패: {str(exc)[:150]}")

        # 동기화 완료 후 최근 4주 계획↔활동 자동 매칭
        try:
            import sqlite3 as _sqlite3
            from datetime import date as _date, timedelta as _td
            from src.training.matcher import match_week_activities
            today = _date.today()
            this_week = today - _td(days=today.weekday())
            with _sqlite3.connect(str(get_db_path()), timeout=30) as conn:
                conn.execute("PRAGMA journal_mode=WAL")
                for w in range(4):
                    match_week_activities(conn, this_week - _td(weeks=w))
                conn.commit()
        except Exception:
            pass

    # ── 배치 실행 ─────────────────────────────────────────────────────

    def _run_one_batch(
        self,
        service: str,
        win_from: str,
        win_to: str,
        garmin_client,
    ) -> tuple[int, int]:
        """단일 날짜 창 동기화. (활동 수, 예상 요청 수) 반환."""
        count = 0
        req_added = 0
        try:
            # isolation_level=None → autocommit: INSERT마다 즉시 commit → 병렬 서비스 간 write lock 경합 해소
            conn = sqlite3.connect(str(get_db_path()), timeout=30, isolation_level=None)
            conn.execute("PRAGMA journal_mode=WAL")
            try:
                if service == "garmin":
                    from src.sync.garmin import sync_activities
                    count = sync_activities(
                        self.config, conn, 7,
                        client=garmin_client,
                        from_date=win_from, to_date=win_to,
                        bg_mode=True,
                    )
                    # 웰니스 동기화 (기간 포함)
                    from src.sync.garmin_wellness_sync import sync_wellness
                    try:
                        sync_wellness(self.config, conn, 7, client=garmin_client,
                                      from_date=win_from, to_date=win_to)
                    except Exception as we:
                        print(f"[garmin] 웰니스 동기화 실패: {we}")
                    req_added = count * 2 + 1 + 7  # list + detail + wellness
                elif service == "strava":
                    from src.sync.strava import sync_activities
                    count = sync_activities(
                        self.config, conn, 7,
                        from_date=win_from, to_date=win_to,
                        bg_mode=True,
                    )
                    req_added = count * 4 + 1   # list + detail + stream + zones
                elif service == "intervals":
                    from src.sync.intervals import sync_activities
                    count = sync_activities(
                        self.config, conn, 7,
                        from_date=win_from, to_date=win_to,
                    )
                    req_added = count * 3 + 1   # list + intervals + streams + power_curve
                elif service == "runalyze":
                    from src.sync.runalyze import sync_activities
                    count = sync_activities(
                        self.config, conn, 7,
                        from_date=win_from, to_date=win_to,
                    )
                    req_added = count * 2 + 1   # list + detail
            finally:
                conn.close()
        except Exception as exc:
            update_job(self.job_id, last_error=str(exc)[:200])
        return count, req_added

    def _garmin_login(self):
        try:
            from src.sync.garmin import _login
            return _login(self.config)
        except Exception as exc:
            print(f"[bg_sync] Garmin 로그인 실패: {exc}")
            return None

    def _interruptible_sleep(self, seconds: float) -> None:
        """중단 가능한 sleep."""
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            if self._stop_event.is_set() or not self._pause_event.is_set():
                return
            time.sleep(min(0.5, end - time.monotonic()))


# ── 공개 API ─────────────────────────────────────────────────────────────

def start_job(
    service: str,
    from_date: str,
    to_date: str,
    config: dict,
) -> str:
    """새 백그라운드 동기화 시작. job_id 반환.

    이미 해당 서비스 스레드가 살아 있으면 기존 job_id 반환.
    """
    with _lock:
        t = _threads.get(service)
        if t and t.is_alive():
            existing = get_active_job(service)
            return existing.id if existing else ""

    job = create_job(service, from_date, to_date)
    thread = BgSyncThread(job.id, config)
    with _lock:
        _threads[service] = thread
    thread.start()
    return job.id


def pause_job(service: str) -> bool:
    with _lock:
        t = _threads.get(service)
    if t and t.is_alive():
        t.pause()
        return True
    return False


def stop_job(service: str) -> bool:
    with _lock:
        t = _threads.get(service)
    if t and t.is_alive():
        t.stop()
        return True
    # 스레드 없으면 DB 상태만 업데이트
    job = get_active_job(service)
    if job:
        update_job(job.id, status="stopped")
    return False


def resume_job(service: str, config: dict) -> bool:
    """일시정지/중지 상태에서 재개. 스레드가 살아 있으면 resume, 없으면 새 스레드 생성."""
    with _lock:
        t = _threads.get(service)
    if t and t.is_alive():
        t.resume()
        return True

    job = get_active_job(service)
    if not job or job.status not in ("paused", "stopped", "rate_limited"):
        return False

    thread = BgSyncThread(job.id, config)
    with _lock:
        _threads[service] = thread
    thread.start()
    return True


def get_status(service: str) -> dict:
    """서비스의 현재 백그라운드 동기화 상태 반환 (UI 폴링용)."""
    job = get_active_job(service)
    if not job:
        return {"active": False}

    retry_sec = get_retry_after_sec(service)
    rl = job.rate_limit
    thread_alive = bool(_threads.get(service) and _threads[service].is_alive())

    return {
        "active": True,
        "job_id": job.id,
        "service": job.service,
        "from_date": job.from_date,
        "to_date": job.to_date,
        "status": job.status,
        "current_from": job.current_from,
        "current_to": job.current_to,
        "completed_days": job.completed_days,
        "total_days": job.total_days,
        "progress_pct": round(job.progress_pct, 1),
        "synced_count": job.synced_count,
        "req_count": job.req_count,
        "rate_limit_15min": rl["per_15min"],
        "rate_limit_daily": rl["per_day"],
        "retry_after_sec": retry_sec,
        "last_error": job.last_error,
        "thread_alive": thread_alive,
        "resumable": job.status in ("paused", "stopped", "rate_limited"),
    }
