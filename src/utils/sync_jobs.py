"""백그라운드 동기화 작업 관리 — DB 기반 상태 추적 (sync_jobs 테이블).

각 작업은 날짜 범위를 window_days 단위 배치로 분할하여 처리한다.
"""
from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional

from src.db_setup import get_db_path
from src.utils.sync_jobs_schema import ensure_ledger


# ── 서비스별 배치 설정 ────────────────────────────────────────────────────
# 공식 한도의 절반을 유효 한도로 사용 (Strava 기준, 나머지는 Strava 절반의 절반)
WINDOW_DAYS: dict[str, int] = {
    "garmin": 14,
    "strava": 14,      # 14일 × ~10활동 = 140 req → 100/15min 한도 이내
    "intervals": 30,
    "runalyze": 14,
}

# 서비스별 유효 API 한도 (공식 한도의 50%)
RATE_LIMITS: dict[str, dict[str, int]] = {
    "strava":    {"per_15min": 100, "per_day": 1000},
    "garmin":    {"per_15min": 50,  "per_day": 500},
    "intervals": {"per_15min": 50,  "per_day": 500},
    "runalyze":  {"per_15min": 50,  "per_day": 500},
}

# 배치 간 대기 (초) — API 부하 방지
INTER_BATCH_SLEEP: dict[str, float] = {
    "garmin": 15.0,
    "strava": 5.0,
    "intervals": 3.0,
    "runalyze": 15.0,
}


@dataclass
class SyncJob:
    """백그라운드 동기화 작업 상태."""

    id: str
    service: str
    from_date: str           # YYYY-MM-DD
    to_date: str             # YYYY-MM-DD
    window_days: int
    current_from: Optional[str]
    status: str              # pending/running/paused/stopped/completed/rate_limited/auth_required/failed
    completed_days: int
    total_days: int
    synced_count: int
    req_count: int           # 예상 API 요청 누적
    created_at: str
    updated_at: str
    retry_after: Optional[str]   # ISO datetime
    last_error: Optional[str]
    error_code: Optional[str] = None
    http_status: Optional[int] = None
    source_path: Optional[str] = None   # manual / bg / auto / cli
    counts_json: Optional[str] = None   # {"activities": n} 결과 카운트
    trigger: Optional[str] = None       # 시작 경로(source_path와 동일 값)
    started_at: Optional[str] = None    # running 최초 전이 시각
    finished_at: Optional[str] = None   # 종료 상태 전이 시각
    result_json: Optional[str] = None   # 재계산 등 작업별 결과(before/after 요약)

    @property
    def progress_pct(self) -> float:
        """완료 비율 (0–100)."""
        if self.total_days <= 0:
            return 0.0
        return min(100.0, self.completed_days / self.total_days * 100)

    @property
    def current_to(self) -> Optional[str]:
        """현재 배치 종료일."""
        if not self.current_from:
            return None
        try:
            wend = date.fromisoformat(self.current_from) + timedelta(days=self.window_days - 1)
            end = date.fromisoformat(self.to_date)
            return min(wend, end).isoformat()
        except ValueError:
            return None

    @property
    def rate_limit(self) -> dict[str, int]:
        return RATE_LIMITS.get(self.service, {"per_15min": 50, "per_day": 500})


# ── 윈도우 분할 ──────────────────────────────────────────────────────────

def windows(from_date: str, to_date: str, window_days: int) -> list[tuple[str, str]]:
    """날짜 범위를 window_days 단위 배치 리스트로 분할.

    Returns:
        [(batch_from, batch_to), ...] — 각 요소는 ISO date 문자열 쌍.
    """
    start = date.fromisoformat(from_date)
    end = date.fromisoformat(to_date)
    result = []
    cur = start
    while cur <= end:
        wend = min(cur + timedelta(days=window_days - 1), end)
        result.append((cur.isoformat(), wend.isoformat()))
        cur = wend + timedelta(days=1)
    return result


_TERMINAL_STATUSES = ("completed", "stopped", "failed", "rate_limited", "auth_required", "cancelled")


# ── DB 헬퍼 ─────────────────────────────────────────────────────────────

_COLS = (
    "id, service, from_date, to_date, window_days, current_from, "
    "status, completed_days, total_days, synced_count, req_count, "
    "created_at, updated_at, retry_after, last_error, "
    "error_code, http_status, source_path, counts_json, trigger, started_at, finished_at, result_json"
)


def _jobs_db_path(user_id: str | None = None) -> str:
    """sync_jobs 전용 DB 경로 — running.db와 별도 파일로 write 경합 방지."""
    return str(get_db_path(user_id).parent / "sync_jobs.db")


def _conn(user_id: str | None = None) -> sqlite3.Connection:
    """sync_jobs.db 전용 커넥션. 테이블 없으면 자동 생성."""
    # user_context.resolve_user_id: 인자 → thread-local → Flask session → "default"
    # bg_sync 스레드는 set_current_user()로 thread-local을 설정하므로 올바른 DB를 사용하게 됨
    try:
        from src.utils.user_context import resolve_user_id
        uid = resolve_user_id(user_id)
    except Exception:
        uid = user_id
    path = _jobs_db_path(uid)
    conn = sqlite3.connect(path, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    ensure_ledger(conn, path)
    return conn


def _row(row: tuple) -> SyncJob:
    return SyncJob(*row)


def cleanup_stale_running_jobs() -> int:
    """프로세스 재시작 시 남아있는 'running'/'pending' 작업을 'stopped'로 정리.

    Returns:
        정리된 작업 수.
    """
    now = datetime.now().isoformat(timespec="seconds")
    with _conn() as conn:
        cur = conn.execute(
            "UPDATE sync_jobs SET status='stopped', updated_at=?, last_error='프로세스 재시작으로 중단됨' "
            "WHERE status IN ('running', 'pending')",
            (now,),
        )
        return cur.rowcount


def cleanup_stale_running_jobs_all_users(older_than_sec: int = 600) -> int:
    """모든 사용자 원장의 오래 갱신 없는 running/pending 작업을 'stopped'로 정리.

    import 시점엔 사용자 컨텍스트가 없어 default 원장만 정리되던 문제를 보완한다.
    다른 워커가 진행 중인 작업을 건드리지 않도록 older_than_sec 이상 갱신 없는 행만 닫는다.
    """
    from src.db_setup import _PROJECT_ROOT

    users_dir = _PROJECT_ROOT / "data" / "users"
    if not users_dir.is_dir():
        return 0
    cutoff = (datetime.now() - timedelta(seconds=older_than_sec)).isoformat(timespec="seconds")
    now = datetime.now().isoformat(timespec="seconds")
    total = 0
    for d in sorted(users_dir.iterdir()):
        if not (d / "sync_jobs.db").exists():
            continue
        try:
            with _conn(d.name) as conn:
                cur = conn.execute(
                    "UPDATE sync_jobs SET status='stopped', updated_at=?, last_error='프로세스 재시작으로 중단됨' "
                    "WHERE status IN ('running', 'pending') AND updated_at < ?",
                    (now, cutoff),
                )
                total += cur.rowcount
        except Exception:
            continue
    return total


# ── CRUD ─────────────────────────────────────────────────────────────────

def create_job(
    service: str, from_date: str, to_date: str,
    *, source_path: str | None = None, job_id: str | None = None,
) -> SyncJob:
    """새 동기화 작업 생성 후 반환."""
    job_id = job_id or str(uuid.uuid4())
    now = datetime.now().isoformat(timespec="seconds")
    wdays = WINDOW_DAYS.get(service, 14)
    start = date.fromisoformat(from_date)
    end = date.fromisoformat(to_date)
    total = max(1, (end - start).days + 1)

    with _conn() as conn:
        # 신규 작업 시작 시 동일 서비스의 기존 미완료 작업을 stopped로 정리
        conn.execute(
            "UPDATE sync_jobs SET status='stopped', updated_at=? "
            "WHERE service=? AND status IN ('pending','paused','stopped','rate_limited')",
            (now, service),
        )
        conn.execute(
            f"INSERT INTO sync_jobs ({_COLS}) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                job_id, service, from_date, to_date, wdays, from_date,
                "pending", 0, total, 0, 0, now, now, None, None,
                None, None, source_path, None, source_path, None, None, None,
            ),
        )
    job = get_job(job_id)
    assert job is not None
    return job


def get_job(job_id: str) -> SyncJob | None:
    with _conn() as conn:
        row = conn.execute(
            f"SELECT {_COLS} FROM sync_jobs WHERE id = ?", (job_id,)
        ).fetchone()
    return _row(row) if row else None


def get_active_job(service: str) -> SyncJob | None:
    """서비스의 active(미완료) 최근 작업 반환."""
    with _conn() as conn:
        row = conn.execute(
            f"SELECT {_COLS} FROM sync_jobs "
            "WHERE service = ? AND status NOT IN ('completed', 'stopped', 'failed', 'cancelled') "
            "ORDER BY created_at DESC LIMIT 1",
            (service,),
        ).fetchone()
    return _row(row) if row else None


def get_latest_job(service: str) -> SyncJob | None:
    """서비스의 가장 최근 갱신된 작업 반환 (상태 무관 — UI 표시용)."""
    with _conn() as conn:
        row = conn.execute(
            f"SELECT {_COLS} FROM sync_jobs "
            "WHERE service = ? "
            "ORDER BY updated_at DESC LIMIT 1",
            (service,),
        ).fetchone()
    return _row(row) if row else None


def update_job(job_id: str, **kwargs) -> None:
    """지정 필드 업데이트."""
    if not kwargs:
        return
    now = kwargs["updated_at"] = datetime.now().isoformat(timespec="seconds")
    status = kwargs.get("status")
    if status in _TERMINAL_STATUSES:
        kwargs.setdefault("finished_at", now)
    set_clause = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [job_id]
    with _conn() as conn:
        conn.execute(f"UPDATE sync_jobs SET {set_clause} WHERE id = ?", values)
        if status == "running":
            conn.execute(
                "UPDATE sync_jobs SET started_at = ? WHERE id = ? AND started_at IS NULL", (now, job_id)
            )


def list_recent_jobs(service: str | None = None, limit: int = 10) -> list[SyncJob]:
    """최근 작업 목록 (최신순)."""
    q = f"SELECT {_COLS} FROM sync_jobs"
    params: list = []
    if service:
        q += " WHERE service = ?"
        params.append(service)
    q += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    with _conn() as conn:
        rows = conn.execute(q, params).fetchall()
    return [_row(r) for r in rows]
