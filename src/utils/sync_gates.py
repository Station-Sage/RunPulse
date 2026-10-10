"""동기화 게이트 — 429/인증 만료 후 재시도 가능 시각(sync_gates 테이블, 사용자별 sync_jobs.db)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

BASE_BACKOFF_SEC = 900
MAX_BACKOFF_SEC = 86400


@dataclass
class Gate:
    service: str
    retry_after: str
    backoff_sec: int
    reason_code: str
    set_at: str
    job_id: str | None

    @property
    def remaining_sec(self) -> int:
        return int((datetime.fromisoformat(self.retry_after) - datetime.now()).total_seconds())


def _conn(user_id: str | None):
    from src.utils.sync_jobs import _conn
    return _conn(user_id)


def gate(service: str, user_id: str | None = None) -> Gate | None:
    """만료되지 않은 게이트. 없거나 만료면 None."""
    with _conn(user_id) as conn:
        row = conn.execute(
            "SELECT service, retry_after, backoff_sec, reason_code, set_at, job_id "
            "FROM sync_gates WHERE service = ?", (service,),
        ).fetchone()
    if not row:
        return None
    g = Gate(*row)
    try:
        return g if g.remaining_sec > 0 else None
    except ValueError:
        return None


def wait_sec(service: str, user_id: str | None = None) -> int | None:
    """재시도 가능까지 남은 초. 없거나 만료면 None."""
    g = gate(service, user_id)
    return g.remaining_sec if g else None


def _put(service: str, seconds: int, reason: str, user_id: str | None) -> None:
    from src.utils.user_context import current_job
    now = datetime.now()
    with _conn(user_id) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO sync_gates (service, retry_after, backoff_sec, reason_code, set_at, job_id) "
            "VALUES (?,?,?,?,?,?)",
            (service, (now + timedelta(seconds=seconds)).isoformat(timespec="seconds"),
             seconds, reason, now.isoformat(timespec="seconds"), current_job()),
        )


def bump_backoff(service: str, *, reason: str = "rate_limited", user_id: str | None = None) -> int:
    """게이트가 활성이면 대기를 2배(최대 24h), 아니면 15분으로 설정하고 새 대기 초를 반환."""
    g = gate(service, user_id)
    seconds = min(g.backoff_sec * 2, MAX_BACKOFF_SEC) if g else BASE_BACKOFF_SEC
    _put(service, seconds, reason, user_id)
    return seconds


def block(service: str, seconds: int, *, reason: str, user_id: str | None = None) -> None:
    """지정 시간 동안 고정 차단(예: runalyze 403 24h)."""
    _put(service, seconds, reason, user_id)


def clear(service: str, user_id: str | None = None) -> None:
    with _conn(user_id) as conn:
        conn.execute("DELETE FROM sync_gates WHERE service = ?", (service,))
