"""동기화 원장 읽기 전용 질의 — 실행 중·마지막 성공·자동 실행 시각을 sync_jobs.db 한 곳에서 낸다(부작용 없음)."""
from __future__ import annotations

from datetime import datetime, timedelta

from src.utils.sync_jobs import _COLS, SyncJob, _conn, _row

STALE_SEC = 600  # updated_at 하트비트가 이 시간 넘게 멈추면 죽은 실행으로 본다
SERVICES = ("garmin", "strava", "intervals", "runalyze")


def busy_job(service: str, user_id: str | None = None) -> SyncJob | None:
    """신선한 pending/running 행(없으면 None). paused·rate_limited 는 실행 중이 아니다."""
    cutoff = (datetime.now() - timedelta(seconds=STALE_SEC)).isoformat(timespec="seconds")
    conn = _conn(user_id)
    try:
        row = conn.execute(
            f"SELECT {_COLS} FROM sync_jobs WHERE service=? AND status IN ('pending','running') "
            "AND updated_at >= ? ORDER BY created_at DESC LIMIT 1",
            (service, cutoff),
        ).fetchone()
    finally:
        conn.close()
    return _row(row) if row else None


def is_busy(service: str, user_id: str | None = None) -> bool:
    return busy_job(service, user_id) is not None


def _latest(sql: str, params: tuple, user_id: str | None) -> str | None:
    conn = _conn(user_id)
    try:
        row = conn.execute(sql, params).fetchone()
    finally:
        conn.close()
    return row[0] if row and row[0] else None


def _dt(val: str | None) -> datetime | None:
    try:
        return datetime.fromisoformat(val) if val else None
    except ValueError:
        return None


def last_success_at(service: str, user_id: str | None = None) -> datetime | None:
    """가장 최근 completed 행의 완료 시각 (finished_at 우선, 없으면 updated_at)."""
    return _dt(_latest(
        "SELECT COALESCE(finished_at, updated_at) AS t FROM sync_jobs "
        "WHERE service=? AND status='completed' ORDER BY t DESC LIMIT 1",
        (service,), user_id,
    ))


def last_auto_run(user_id: str | None = None) -> datetime | None:
    """자동 동기화가 마지막으로 시작된 시각."""
    return _dt(_latest("SELECT MAX(created_at) FROM sync_jobs WHERE trigger='auto'", (), user_id))


def legacy_card_states(user_id: str | None = None) -> dict[str, dict]:
    """구 화면 소스 카드용 상태 {service: {is_running, last_sync_at, cooldown_*, last_error, last_count, last_partial}}."""
    from src.utils.sync_policy import check_incremental_guard

    out: dict[str, dict] = {}
    for svc in SERVICES:
        last = last_success_at(svc, user_id)
        guard = check_incremental_guard(svc, last)
        conn = _conn(user_id)
        try:
            row = conn.execute(
                "SELECT status, synced_count, error_code, last_error FROM sync_jobs "
                "WHERE service=? AND status IN ('completed','failed','stopped','auth_required','rate_limited') "
                "ORDER BY created_at DESC LIMIT 1",
                (svc,),
            ).fetchone()
        finally:
            conn.close()
        status, count, code, err = row if row else (None, 0, None, None)
        out[svc] = {
            "is_running": is_busy(svc, user_id),
            "last_sync_at": last.isoformat(timespec="seconds") if last else None,
            "cooldown_sec": guard.retry_after_sec if not guard.allowed else None,
            "cooldown_msg": guard.message_ko if not guard.allowed else None,
            "last_error": None if status == "completed" else err,
            "last_count": count or 0,
            "last_partial": status == "completed" and code == "partial_rate_limited",
        }
    return out
