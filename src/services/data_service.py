"""Data 영역(`/v2/data/*`) 읽기 서비스 — 소스 카드·소스 상세·개요 요약·동기화 기록.

연결/동기화 상태는 sync_state_service 계약을 그대로 쓰고, 여기서는 보관 데이터 수치(건수·커버리지·대표 지표)와
작업 원장 기록만 덧붙인다. 쓰기(연결·해제·토글)는 이 모듈 범위가 아니다. 설계: 40-v2 design §2.4·§7.3.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime

from src.services import provider_status_service, sync_state_service
from src.utils.sync_jobs import SyncJob, list_recent_jobs

SOURCES = sync_state_service.SOURCES
_FAILED = ("failed", "rate_limited", "auth_required")


def _scalar(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> int:
    try:
        return conn.execute(sql, params).fetchone()[0] or 0
    except sqlite3.OperationalError:
        return 0


def _counts(conn: sqlite3.Connection, provider: str) -> dict:
    return {
        "activities": _scalar(conn, "SELECT COUNT(*) FROM activity_summaries WHERE source=?", (provider,)),
        "wellness_days": _scalar(
            conn, "SELECT COUNT(DISTINCT entity_date) FROM source_payloads"
            " WHERE source=? AND entity_type LIKE 'wellness%' AND entity_date IS NOT NULL", (provider,)),
        "streams": _scalar(conn, "SELECT COUNT(DISTINCT activity_id) FROM activity_streams WHERE source=?", (provider,)),
        "laps": _scalar(conn, "SELECT COUNT(DISTINCT activity_id) FROM activity_laps WHERE source=?", (provider,)),
    }


def run_dict(job: SyncJob) -> dict:
    """원장 행 → 기록 행. counts는 counts_json이 있을 때만 채운다."""
    try:
        counts = json.loads(job.counts_json) if job.counts_json else None
    except ValueError:
        counts = None
    return {
        "id": job.id, "provider": job.service, "status": job.status,
        "from_date": job.from_date, "to_date": job.to_date,
        "trigger": job.trigger or job.source_path,
        "started_at": job.started_at or job.created_at, "finished_at": job.finished_at,
        "synced_count": job.synced_count, "counts": counts,
        "error_code": job.error_code, "last_error": job.last_error,
    }


def runs(provider: str | None = None, errors_only: bool = False, limit: int = 20) -> list[dict]:
    """최근 동기화 기록(최신순). errors_only면 실패·한도·인증 필요만."""
    limit = max(1, min(limit, 100))
    jobs = list_recent_jobs(provider, limit=limit * 4 if errors_only else limit)
    if errors_only:
        jobs = [j for j in jobs if j.status in _FAILED][:limit]
    return [run_dict(j) for j in jobs]


def sources(conn: sqlite3.Connection, config: dict) -> list[dict]:
    """소스 카드 4장 — 연결·동기화 켬 두 축과 보관 건수를 함께."""
    state = {s["provider"]: s for s in sync_state_service.get_sync_state(conn, config)["sources"]}
    return [{**state[p], "activity_count": _scalar(
        conn, "SELECT COUNT(*) FROM activity_summaries WHERE source=?", (p,))} for p in SOURCES]


def source_detail(conn: sqlite3.Connection, config: dict, provider: str, *,
                  months: int = 12, today: str | None = None) -> dict | None:
    """소스 상세 — 상태·건수·최근 12개월 커버리지·최근 기록. 모르는 소스는 None."""
    if provider not in SOURCES:
        return None
    card = next(s for s in sources(conn, config) if s["provider"] == provider)
    now = datetime.fromisoformat(today) if today else datetime.now()
    y, m = now.year, now.month - (months - 1)
    while m < 1:
        y, m = y - 1, m + 12
    cov = provider_status_service.get_provider_coverage(conn, f"{y:04d}-{m:02d}", now.date().isoformat(), config)
    row = next(p for p in cov["providers"] if p["provider"] == provider)
    first, last = (conn.execute(
        "SELECT MIN(substr(start_time,1,10)), MAX(substr(start_time,1,10)) FROM activity_summaries WHERE source=?",
        (provider,)).fetchone())
    return {
        **card,
        "counts": _counts(conn, provider),
        "coverage": {"first": first, "last": last, "months": [
            {"month": mo, "count": n} for mo, n in zip(cov["months"], row["counts"])]},
        "recent_runs": runs(provider, limit=5),
    }


def summary(conn: sqlite3.Connection, config: dict) -> dict:
    """개요 타일 — 통합 활동 수·웰니스 일수·기간·저장 용량 + 최근 기록 5건."""
    first, last, acts = conn.execute(
        "SELECT MIN(substr(start_time,1,10)), MAX(substr(start_time,1,10)), COUNT(*) FROM activity_summaries"
    ).fetchone()
    try:
        page_count = conn.execute("PRAGMA page_count").fetchone()[0]
        page_size = conn.execute("PRAGMA page_size").fetchone()[0]
    except sqlite3.OperationalError:
        page_count = page_size = 0
    return {
        "activities": acts,
        "wellness_days": _scalar(conn, "SELECT COUNT(*) FROM daily_wellness"),
        "period": {"first": first, "last": last},
        "storage_bytes": page_count * page_size,
        "recent_runs": runs(limit=5),
    }
