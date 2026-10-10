"""수동 증분 동기화 트리거 — 소스별 판정(plan)과 bg_sync 시작(trigger). v1/v2 공용.

판정 순서(고정): not_connected → disabled → running → cooldown → rate_limited.
시작일은 서버가 activity_summaries 기준으로 결정한다(days_since_last_sync).
"""
from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

log = logging.getLogger(__name__)

ALL_SOURCES = ("garmin", "strava", "intervals", "runalyze")


@dataclass(frozen=True)
class SkipReason:
    provider: str
    code: str  # not_connected|disabled|running|cooldown|rate_limited|start_failed
    message_ko: str
    retry_after_sec: int | None = None
    job_id: str | None = None

    def to_dict(self) -> dict:
        d = {"provider": self.provider, "code": self.code, "message_ko": self.message_ko}
        if self.retry_after_sec is not None:
            d["retry_after_sec"] = self.retry_after_sec
        if self.job_id:
            d["job_id"] = self.job_id
        return d


@dataclass(frozen=True)
class TriggerResult:
    runs: list[dict]
    skipped: list[SkipReason]


def days_since_last_sync(db_file: Path, sources: list[str]) -> int:
    """마지막 활동 이후 일수(+2 여유, 1~365). 데이터 없으면 7."""
    if not db_file.exists():
        return 7
    try:
        with sqlite3.connect(str(db_file)) as conn:
            ph = ",".join("?" * len(sources))
            row = conn.execute(
                f"SELECT MAX(start_time) FROM activity_summaries WHERE source IN ({ph})",
                sources,
            ).fetchone()
        if not row or not row[0]:
            return 7
        last = date.fromisoformat(str(row[0])[:10])
        return max(1, min((date.today() - last).days + 2, 365))
    except Exception:
        return 7


def _checkers() -> dict:
    from src.sync.garmin import check_garmin_connection
    from src.sync.intervals import check_intervals_connection
    from src.sync.runalyze import check_runalyze_connection
    from src.sync.strava import check_strava_connection
    return {
        "garmin": check_garmin_connection,
        "strava": check_strava_connection,
        "intervals": check_intervals_connection,
        "runalyze": check_runalyze_connection,
    }


def plan_incremental(
    config: dict,
    user_id: str,
    sources: list[str] | None,
    today: date | None = None,
    db_file: Path | None = None,
) -> tuple[list[str], dict[str, str], list[SkipReason]]:
    """판정만 수행(부작용 없음). (시작할 소스, 소스별 from_date, skip 목록)."""
    from src.utils.config import enabled_sources
    from src.utils.sync_jobs import get_active_job
    from src.utils.sync_policy import check_incremental_guard
    from src.utils.sync_gates import wait_sec
    from src.utils.sync_state import get_last_sync_at
    from src.utils.sync_ledger_query import is_busy
    if db_file is None:
        from src.web.helpers import db_path
        db_file = db_path()

    today = today or date.today()
    targets = [s for s in (sources or ALL_SOURCES) if s in ALL_SOURCES]
    checkers = _checkers()
    on = enabled_sources(config)
    start: list[str] = []
    from_dates: dict[str, str] = {}
    skipped: list[SkipReason] = []

    for src in targets:
        conn_status = checkers[src](config)
        if not conn_status["ok"]:
            skipped.append(SkipReason(src, "not_connected", f"미연결 ({conn_status['status']})"))
            continue
        if src not in on:
            skipped.append(SkipReason(src, "disabled", "동기화 대상에서 꺼져 있어요"))
            continue
        if is_busy(src, user_id):
            job = get_active_job(src)
            skipped.append(SkipReason(src, "running", "이미 동기화 중이에요", job_id=job.id if job else None))
            continue
        guard = check_incremental_guard(src, get_last_sync_at(src, user_id))
        if not guard.allowed:
            skipped.append(SkipReason(src, "cooldown", guard.message_ko or "정책 제한", guard.retry_after_sec))
            continue
        wait = wait_sec(src, user_id)
        if wait:
            skipped.append(SkipReason(src, "rate_limited", "요청 제한 대기 중이에요", wait))
            continue
        from_dates[src] = (today - timedelta(days=days_since_last_sync(db_file, [src]))).isoformat()
        start.append(src)
    return start, from_dates, skipped


def trigger_incremental(
    config: dict,
    user_id: str,
    sources: list[str] | None,
    source_path: str = "v2",
) -> TriggerResult:
    """plan → 소스별 bg_sync 시작. 한 소스 시작 실패는 start_failed로 담고 나머지는 계속."""
    from src.web.bg_sync import _start_or_existing

    today = date.today()
    start, from_dates, skipped = plan_incremental(config, user_id, sources, today)
    skipped = list(skipped)
    runs: list[dict] = []
    for src in start:
        try:
            job_id, created = _start_or_existing(
                src, from_dates[src], today.isoformat(), config, user_id, source_path)
        except Exception as exc:
            log.warning("[sync_trigger] %s 시작 실패: %s", src, exc)
            skipped.append(SkipReason(src, "start_failed", "동기화를 시작하지 못했어요"))
            continue
        if not created:
            skipped.append(SkipReason(src, "running", "이미 동기화 중이에요", job_id=job_id or None))
            continue
        runs.append({"id": job_id, "provider": src, "state": "queued",
                     "from": from_dates[src], "to": today.isoformat()})
    return TriggerResult(runs=runs, skipped=skipped)
