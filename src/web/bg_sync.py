"""백그라운드 기간 동기화 실행기 — 서비스별 Thread + pause/stop 제어.

특징:
- Garmin 클라이언트 재사용 (배치 간 재인증 없음)
- pause_event / stop_event 로 활동 단위 중단 가능
- rate_limit 자동 대기 후 재개
- sync_jobs 테이블로 진행 상태 추적
"""
from __future__ import annotations

import json
import logging
import sqlite3
import threading
import time
from datetime import date, datetime, timedelta
from typing import Optional

log = logging.getLogger(__name__)

from src.db_setup import get_db_path
from src.utils.sync_jobs import (
    SyncJob,
    INTER_BATCH_SLEEP,
    cleanup_stale_running_jobs,
    cleanup_stale_running_jobs_all_users,
    create_job,
    get_active_job,
    get_job,
    get_latest_job,
    update_job,
    windows,
)
from src.sync.sync_errors import SyncSourceError, classify_exception
from src.utils.sync_state import get_retry_after_sec

# ── 전역 스레드 레지스트리 ────────────────────────────────────────────────
_threads: dict[tuple[str, str], "BgSyncThread"] = {}  # (user_id, service) → 스레드
_lock = threading.Lock()


class _Starting:
    """start 진행 중 자리표시 — is_alive()가 항상 True."""

    def is_alive(self) -> bool:
        return True


_STARTING = _Starting()


def _find_thread(service: str, user_id: str | None = None):
    """user_id 지정 시 해당 사용자 스레드, 생략 시 service가 같은 아무 스레드(v1 호환). _lock 안에서 호출."""
    if user_id is not None:
        return _threads.get((user_id, service))
    for (_, svc), t in _threads.items():
        if svc == service:
            return t
    return None

# 프로세스 시작 시 이전 실행에서 남은 stale "running" 작업 정리
try:
    _cleaned = cleanup_stale_running_jobs() + cleanup_stale_running_jobs_all_users()
    if _cleaned:
        log.info("[bg_sync] stale 작업 %d개 정리됨", _cleaned)
except Exception:
    pass


# ── 스레드 ───────────────────────────────────────────────────────────────

class BgSyncThread(threading.Thread):
    """서비스별 백그라운드 동기화 스레드."""

    def __init__(self, job_id: str, config: dict, user_id: str = "default") -> None:
        super().__init__(daemon=True, name=f"bgsync-{job_id[:8]}")
        self.job_id = job_id
        self.config = config
        self.user_id = user_id
        self._pause_event = threading.Event()
        self._stop_event = threading.Event()
        self._cancelled = False   # 소스 제외로 인한 취소 — 재개 불가 상태로 마감
        self._pause_event.set()   # 기본: 실행 상태
        self._last_garmin_login: float = 0.0  # monotonic timestamp of last garmin login
        self._batch_error: SyncSourceError | None = None  # 일반 예외로 끝난 첫 배치 오류

    def pause(self) -> None:
        self._pause_event.clear()

    def resume(self) -> None:
        self._pause_event.set()

    def stop(self) -> None:
        self._stop_event.set()
        self._pause_event.set()   # 일시정지 해제 → 루프 종료 진행

    def cancel(self) -> None:
        self._cancelled = True
        self.stop()

    def _stopped(self, **kwargs) -> None:
        update_job(self.job_id, status="cancelled" if self._cancelled else "paused", **kwargs)

    def run(self) -> None:
        from src.utils.user_context import set_current_user
        set_current_user(self.user_id)
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
                if _threads.get((self.user_id, job.service)) is self:
                    _threads.pop((self.user_id, job.service), None)

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
                update_job(self.job_id, status="auth_required",
                        last_error="Garmin 토큰 만료 또는 없음. /connect/garmin에서 재로그인하세요.")
                return

        total_synced = job.synced_count
        total_req = job.req_count
        job_from = job.from_date  # progress_cb 클로저에서 사용

        def _progress_cb(day_str: str, synced: int = 0, req: int = 0) -> None:
            """날짜별 실시간 진행 업데이트 콜백."""
            completed = (
                date.fromisoformat(day_str) - date.fromisoformat(job_from)
            ).days + 1
            kwargs: dict = {"completed_days": completed, "current_from": day_str}
            if synced:
                kwargs["synced_count"] = synced
            if req:
                kwargs["req_count"] = req
            update_job(self.job_id, **kwargs)

        for win_from, win_to in pending:
            # 1) 중지 확인
            if self._stop_event.is_set():
                self._stopped(current_from=win_from)
                return

            # 2) 일시정지 대기
            if not self._pause_event.is_set():
                update_job(self.job_id, status="paused")
                self._pause_event.wait()
                if self._stop_event.is_set():
                    self._stopped(current_from=win_from)
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
                    self._stopped(current_from=win_from)
                    return
                update_job(
                    self.job_id, status="running",
                    retry_after=None, last_error=None,
                )

            # 4) 배치 실행
            count, req_added, rate_limited = self._run_one_batch(
                job.service, win_from, win_to, garmin_client,
                progress_cb=_progress_cb,
                total_synced=total_synced,
                total_req=total_req,
            )
            total_synced += count
            total_req += req_added

            err = getattr(self, "_source_error", None)
            if err is not None:
                update_job(
                    self.job_id, status="failed", error_code=err.code,
                    http_status=err.http_status, last_error=str(err)[:300],
                    synced_count=total_synced, req_count=total_req,
                )
                return

            # 4-1) rate limit 발생 시 즉시 중단
            if rate_limited:
                update_job(
                    self.job_id,
                    status="rate_limited",
                    current_from=win_from,
                    synced_count=total_synced,
                    req_count=total_req,
                    last_error="API 429 — 배치 중단. rate limit 해제 후 재개하세요.",
                )
                return

            # 5) 윈도우 완료 후 최종 진행 업데이트
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

        if self._batch_error is not None and total_synced == 0:
            err = self._batch_error
            update_job(
                self.job_id, status="failed", error_code=err.code,
                http_status=err.http_status, last_error=str(err)[:300],
            )
            return

        update_job(
            self.job_id, status="completed",
            counts_json=json.dumps({"activities": total_synced}),
        )

        # 동기화 완료 후 메트릭 자동 재계산 + 재동기화 플래그 해제
        try:
            import sqlite3 as _sqlite3
            from src.metrics import engine as metrics_engine
            from datetime import date as _date
            with _sqlite3.connect(str(get_db_path(self.user_id)), timeout=30) as conn:
                conn.execute("PRAGMA journal_mode=WAL")
                # 오늘 날짜를 항상 포함하여 메트릭 계산
                end = max(job.to_date, _date.today().isoformat())
                metrics_engine.run_for_date_range(conn, job.from_date, end)
                # 오늘 예측 스냅샷(전향 평가용, P7-PRED-63) — 실패해도 동기화는 계속
                try:
                    from src.services.prediction_snapshot_service import record_snapshots
                    record_snapshots(conn, _date.today().isoformat())
                except Exception as snap_exc:  # noqa: BLE001
                    update_job(self.job_id, last_error=f"예측 스냅샷 실패: {str(snap_exc)[:150]}")
                # 스키마 마이그레이션 후 재동기화 플래그 해제
                from src.db_setup import clear_needs_resync
                clear_needs_resync(conn)
                conn.commit()
        except Exception as exc:
            update_job(self.job_id, last_error=f"메트릭 계산 실패: {str(exc)[:150]}")
        else:
            from src.services.narrative_warm import warm_in_background
            warm_in_background(str(get_db_path(self.user_id)), date.today().isoformat(), self.config)

        # 동기화 완료 후 최근 4주 계획↔활동 자동 매칭
        try:
            import sqlite3 as _sqlite3
            from datetime import date as _date, timedelta as _td
            from src.training.matcher import match_week_activities
            today = _date.today()
            this_week = today - _td(days=today.weekday())
            with _sqlite3.connect(str(get_db_path(self.user_id)), timeout=30) as conn:
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
        progress_cb=None,
        total_synced: int = 0,
        total_req: int = 0,
    ) -> tuple[int, int, bool]:
        """단일 날짜 창 동기화. (활동 수, 예상 요청 수, rate_limited 여부) 반환."""
        count = 0
        req_added = 0
        try:
            from garminconnect import GarminConnectTooManyRequestsError as _G429
        except ImportError:
            _G429 = type(None)

        log.info("[bg_sync] 배치 시작: service=%s, %s ~ %s", service, win_from, win_to)
        try:
            conn = sqlite3.connect(str(get_db_path(self.user_id)), timeout=30, isolation_level=None)
            conn.execute("PRAGMA journal_mode=WAL")
            try:
                if service == "garmin":
                    # 45분 이상 경과 시에만 재인증 — auth API 429 방지
                    _RELOGIN_INTERVAL = 45 * 60  # seconds
                    elapsed = time.monotonic() - self._last_garmin_login
                    if elapsed >= _RELOGIN_INTERVAL:
                        try:
                            from src.sync.garmin_auth import _tokenstore_path
                            ts = str(_tokenstore_path(self.config))
                            log.info("[bg_sync] 토큰 갱신 시도 (경과 %.0fs): tokenstore=%s", elapsed, ts)
                            garmin_client.login(tokenstore=ts)
                            self._last_garmin_login = time.monotonic()
                            log.info("[bg_sync] 토큰 갱신 성공")
                        except Exception as _te:
                            log.warning("[bg_sync] 토큰 갱신 실패 (계속 진행): %s", _te)
                    else:
                        log.debug("[bg_sync] 토큰 최근 갱신됨 (%.0fs 전) — 재인증 스킵", elapsed)
                    from src.sync.garmin import sync_activities, sync_wellness
                    log.info("[bg_sync] sync_activities 호출: %s ~ %s", win_from, win_to)
                    count = sync_activities(
                        self.config, conn, 7,
                        client=garmin_client,
                        from_date=win_from, to_date=win_to,
                        bg_mode=True,
                    )
                    log.info("[bg_sync] sync_activities 완료: count=%d", count)
                    # wellness: 날짜별로 개별 호출하여 실시간 진행률 갱신
                    cur = date.fromisoformat(win_from)
                    win_end = date.fromisoformat(win_to)
                    while cur <= win_end:
                        day = cur.isoformat()
                        try:
                            log.info("[bg_sync] sync_wellness 호출: %s", day)
                            sync_wellness(self.config, conn, 7, client=garmin_client,
                                          from_date=day, to_date=day)
                        except _G429:
                            raise  # 429는 위로 전파
                        except Exception as we:
                            log.warning("[bg_sync] 웰니스 동기화 실패 (%s): %s", day, we)
                        if progress_cb:
                            progress_cb(day, total_synced + count, total_req + req_added)
                        cur += timedelta(days=1)
                    try:
                        from src.sync.garmin_maxmet_sync import sync_vo2max_range
                        sync_vo2max_range(conn, garmin_client, win_from, win_to)
                    except _G429:
                        raise
                    except Exception as me:
                        log.warning("[bg_sync] VO2max 동기화 실패: %s", me)
                    req_added = count * 2 + 1 + 8
                elif service == "strava":
                    from src.sync.strava import sync_activities
                    count = sync_activities(
                        self.config, conn, 7,
                        from_date=win_from, to_date=win_to,
                        bg_mode=True,
                    )
                    if progress_cb:
                        progress_cb(win_to, total_synced + count, total_req + req_added)
                    req_added = count * 4 + 1
                elif service == "intervals":
                    from src.sync.intervals import sync_activities
                    count = sync_activities(
                        self.config, conn, 7,
                        from_date=win_from, to_date=win_to,
                    )
                    if progress_cb:
                        progress_cb(win_to, total_synced + count, total_req + req_added)
                    req_added = count * 3 + 1
                elif service == "runalyze":
                    from src.sync.runalyze import sync_activities
                    count = sync_activities(
                        self.config, conn, 7,
                        from_date=win_from, to_date=win_to,
                    )
                    if progress_cb:
                        progress_cb(win_to, total_synced + count, total_req + req_added)
                    req_added = count * 2 + 1
            finally:
                conn.close()
        except _G429 as exc:
            from src.sync.garmin_helpers import _handle_rate_limit
            _handle_rate_limit(service, source_id=f"{win_from}~{win_to}")
            log.warning("[bg_sync] 429 발생 — 배치 중단: %s", exc)
            update_job(self.job_id, last_error=f"429 발생: {str(exc)[:150]}")
            return count, req_added, True  # rate_limited = True
        except SyncSourceError as exc:
            log.warning("[bg_sync] 소스 실패 %s: %s", exc.code, exc)
            if exc.code == "rate_limited":
                update_job(self.job_id, last_error=str(exc)[:200])
                return count, req_added, True
            self._source_error = exc
            return count, req_added, False
        except Exception as exc:
            log.error("[bg_sync] 배치 오류: %s", exc, exc_info=True)
            update_job(self.job_id, last_error=str(exc)[:200])
            if self._batch_error is None:
                code, http = classify_exception(exc)
                self._batch_error = SyncSourceError(code, str(exc)[:200], http)
        log.info("[bg_sync] 배치 완료: service=%s, count=%d", service, count)
        return count, req_added, False  # rate_limited = False

    def _garmin_login(self):
        log.info("[bg_sync] Garmin 로그인 시작 (user_id=%s)", self.user_id)
        try:
            from src.sync.garmin import _login
            client = _login(self.config)
            log.info("[bg_sync] Garmin 로그인 성공")
            return client
        except Exception as exc:
            from src.sync.garmin_auth import GarminAuthRequired
            try:
                from garminconnect import GarminConnectTooManyRequestsError
            except ImportError:
                GarminConnectTooManyRequestsError = type(None)

            if isinstance(exc, GarminConnectTooManyRequestsError):
                from src.sync.garmin_helpers import _handle_rate_limit
                _handle_rate_limit("garmin")
                log.warning("[bg_sync] Garmin 429 — 작업 중단: %s", exc)
                update_job(self.job_id, status="rate_limited",
                          last_error="Garmin 429 — rate limit 대기 중. 자동 재시도하지 않습니다.")
            elif isinstance(exc, GarminAuthRequired):
                log.error("[bg_sync] Garmin 재인증 필요: %s", exc)
                update_job(self.job_id, status="auth_required",
                          last_error="Garmin 재인증 필요. /connect/garmin에서 로그인하세요.")
            else:
                log.error("[bg_sync] Garmin 로그인 실패 (예상치 못한 오류): %s", exc, exc_info=True)
                update_job(self.job_id, last_error=str(exc)[:200])
            return None
            
    def _interruptible_sleep(self, seconds: float) -> None:
        """중단 가능한 sleep."""
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            if self._stop_event.is_set() or not self._pause_event.is_set():
                return
            time.sleep(min(0.5, end - time.monotonic()))


# ── 공개 API ─────────────────────────────────────────────────────────────

def _start_or_existing(
    service: str,
    from_date: str,
    to_date: str,
    config: dict,
    user_id: str = "default",
    source_path: str = "bg",
) -> tuple[str, bool]:
    """(job_id, created). 생존 검사와 스레드 등록을 락 하나로 묶어 중복 시작 경쟁을 막는다."""
    key = (user_id, service)
    with _lock:
        t = _threads.get(key)
        if t is not None:
            if t is _STARTING or t.is_alive():
                existing = get_active_job(service)
                return (existing.id if existing else ""), False
            _threads.pop(key, None)
        _threads[key] = _STARTING
    try:
        job = create_job(service, from_date, to_date, source_path=source_path)
        thread = BgSyncThread(job.id, config, user_id=user_id)
        with _lock:
            _threads[key] = thread
        thread.start()
    except Exception:
        with _lock:
            if _threads.get(key) is _STARTING:
                _threads.pop(key, None)
        raise
    return job.id, True


def start_job(
    service: str,
    from_date: str,
    to_date: str,
    config: dict,
    user_id: str = "default",
    source_path: str = "bg",
) -> str:
    """새 백그라운드 동기화 시작. job_id 반환.

    이미 해당 (사용자, 서비스) 스레드가 살아 있으면 기존 job_id 반환.
    """
    return _start_or_existing(service, from_date, to_date, config, user_id, source_path)[0]


def pause_job(service: str, user_id: str | None = None) -> bool:
    with _lock:
        t = _find_thread(service, user_id)
    if isinstance(t, BgSyncThread) and t.is_alive():
        t.pause()
        return True
    return False


def stop_job(service: str, user_id: str | None = None) -> bool:
    with _lock:
        t = _find_thread(service, user_id)
    if isinstance(t, BgSyncThread) and t.is_alive():
        t.stop()
        return True
    # 스레드 없으면 DB 상태만 업데이트
    job = get_active_job(service)
    if job:
        update_job(job.id, status="stopped")
    return False


def cancel_job(service: str, user_id: str | None = None, reason: str = "source_disabled") -> list[str]:
    """소스 제외로 활성 작업을 cancelled(재개 불가)로 마감한다. 취소한 job_id 목록 반환."""
    ids = []
    job = get_active_job(service)
    while job is not None and job.id not in ids:
        ids.append(job.id)
        job = None
        with _lock:
            t = _find_thread(service, user_id)
        if isinstance(t, BgSyncThread) and t.is_alive():
            t.cancel()
            t.join(timeout=5)
        update_job(ids[-1], status="cancelled", error_code=reason)
        job = get_active_job(service)
    return ids


def resume_job(service: str, config: dict, user_id: str = "default") -> bool:
    """일시정지/중지 상태에서 재개. 스레드가 살아 있으면 resume, 없으면 새 스레드 생성."""
    with _lock:
        t = _find_thread(service, user_id)
    if isinstance(t, BgSyncThread) and t.is_alive():
        t.resume()
        return True

    job = get_active_job(service)
    if not job or job.status not in ("paused", "stopped", "rate_limited"):
        return False

    thread = BgSyncThread(job.id, config, user_id=user_id)
    with _lock:
        _threads[(user_id, service)] = thread
    thread.start()
    return True


def start_basic_sync(
    sources: list[str],
    from_dates: dict[str, str],
    to_date: str,
    config: dict,
    user_id: str = "default",
    source_path: str = "bg",
) -> dict[str, str]:
    """여러 서비스 기본 동기화를 백그라운드로 시작. {service: job_id} 반환."""
    from src.utils.config import enabled_sources
    on = enabled_sources(config)
    result = {}
    for service in sources:
        if service not in on:
            continue          # 동기화 끈 소스(config.sync_sources)
        from_date = from_dates.get(service, to_date)
        job_id = start_job(service, from_date, to_date, config, user_id, source_path)
        if job_id:
            result[service] = job_id
    return result


def get_status(service: str, user_id: str | None = None) -> dict:
    """서비스의 현재 백그라운드 동기화 상태 반환 (UI 폴링용)."""
    job = get_latest_job(service)
    if not job:
        return {"active": False}

    retry_sec = get_retry_after_sec(service)
    rl = job.rate_limit
    with _lock:
        t = _find_thread(service, user_id)
    thread_alive = bool(t and t.is_alive())

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
