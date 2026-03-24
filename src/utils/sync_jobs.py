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
    "garmin": 5.0,
    "strava": 3.0,
    "intervals": 1.5,
    "runalyze": 10.0,
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
    status: str              # pending / running / paused / stopped / completed / rate_limited
    completed_days: int
    total_days: int
    synced_count: int
    req_count: int           # 예상 API 요청 누적
    created_at: str
    updated_at: str
    retry_after: Optional[str]   # ISO datetime
    last_error: Optional[str]

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


# ── DB 헬퍼 ─────────────────────────────────────────────────────────────

_COLS = (
    "id, service, from_date, to_date, window_days, current_from, "
    "status, completed_days, total_days, synced_count, req_count, "
    "created_at, updated_at, retry_after, last_error"
)


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(get_db_path()), timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _row(row: tuple) -> SyncJob:
    return SyncJob(*row)


# ── CRUD ─────────────────────────────────────────────────────────────────

def create_job(service: str, from_date: str, to_date: str) -> SyncJob:
    """새 동기화 작업 생성 후 반환."""
    job_id = str(uuid.uuid4())
    now = datetime.now().isoformat(timespec="seconds")
    wdays = WINDOW_DAYS.get(service, 14)
    start = date.fromisoformat(from_date)
    end = date.fromisoformat(to_date)
    total = max(1, (end - start).days + 1)

    with _conn() as conn:
        conn.execute(
            f"INSERT INTO sync_jobs ({_COLS}) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                job_id, service, from_date, to_date, wdays, from_date,
                "pending", 0, total, 0, 0, now, now, None, None,
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
            "WHERE service = ? AND status NOT IN ('completed', 'stopped') "
            "ORDER BY created_at DESC LIMIT 1",
            (service,),
        ).fetchone()
    return _row(row) if row else None


def update_job(job_id: str, **kwargs) -> None:
    """지정 필드 업데이트."""
    if not kwargs:
        return
    kwargs["updated_at"] = datetime.now().isoformat(timespec="seconds")
    set_clause = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [job_id]
    with _conn() as conn:
        conn.execute(f"UPDATE sync_jobs SET {set_clause} WHERE id = ?", values)


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
