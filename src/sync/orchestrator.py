"""통합 sync 진입점."""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timedelta, timezone

from src.sync.sync_result import SyncResult
from src.sync._helpers import record_sync_job
from src.sync import dedup

log = logging.getLogger(__name__)


def full_sync(
    conn: sqlite3.Connection,
    sources: list[str] = None,
    days: int = 7,
    *,
    include_streams: bool = False,
    api_clients: dict = None,
    configs: dict = None,
) -> dict[str, list[SyncResult]]:
    """모든 소스를 순차적으로 sync.

    Args:
        conn: SQLite connection
        sources: sync할 소스 목록 (기본: 전체)
        days: 날짜 범위
        include_streams: 스트림 데이터 포함 여부
        api_clients: {"garmin": garmin_api, ...}
        configs: {"strava": {...}, "intervals": {...}, ...}

    Returns: {source: [SyncResult, ...]}
    """
    if sources is None:
        sources = ["garmin", "strava", "intervals", "runalyze"]
    if api_clients is None:
        api_clients = {}
    if configs is None:
        configs = {}

    results: dict[str, list[SyncResult]] = {}
    from_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    to_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    for source in sources:
        source_results: list[SyncResult] = []
        try:
            if source == "garmin":
                api = api_clients.get("garmin")
                if api:
                    from src.sync import garmin_activity_sync, garmin_wellness_sync
                    source_results.append(
                        garmin_activity_sync.sync(conn, api, days=days, include_streams=include_streams)
                    )
                    source_results.append(
                        garmin_wellness_sync.sync(conn, api, days=days)
                    )
                else:
                    source_results.append(SyncResult(
                        source="garmin", job_type="activity", status="skipped",
                        last_error="No Garmin API client",
                    ))

            elif source == "strava":
                from src.sync import strava_activity_sync
                source_results.append(
                    strava_activity_sync.sync(
                        conn, days=days, include_streams=include_streams,
                        config=configs.get("strava"),
                    )
                )

            elif source == "intervals":
                from src.sync import intervals_activity_sync
                cfg = configs.get("intervals")
                source_results.append(
                    intervals_activity_sync.sync(conn, days=days, include_streams=include_streams, config=cfg)
                )
                source_results.append(
                    intervals_activity_sync.sync_wellness(conn, days=days, config=cfg)
                )

            elif source == "runalyze":
                from src.sync import runalyze_activity_sync
                source_results.append(
                    runalyze_activity_sync.sync(conn, days=days, config=configs.get("runalyze"))
                )

        except Exception as e:
            log.error("[orchestrator] %s sync failed: %s", source, e)
            source_results.append(SyncResult(
                source=source, job_type="activity", status="failed", last_error=str(e),
            ))

        # sync_jobs 기록
        for sr in source_results:
            try:
                record_sync_job(conn, sr.to_sync_job_dict(from_date, to_date))
                conn.commit()
            except Exception as e:
                log.warning("[orchestrator] Failed to record sync job: %s", e)

        results[source] = source_results

    # Dedup
    try:
        dedup.run(conn)
    except Exception as e:
        log.error("[orchestrator] Dedup failed: %s", e)

    return results
