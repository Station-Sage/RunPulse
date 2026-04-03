"""Orchestrator 내부 어댑터 — Extractor 출력을 db_helpers 인터페이스에 연결."""

from __future__ import annotations

import logging
import sqlite3
from typing import Any

from src.utils.db_helpers import (
    upsert_activity,
    upsert_metrics_batch,
    upsert_laps_batch,
    upsert_streams_batch,
    upsert_best_efforts_batch,
    upsert_daily_wellness,
    upsert_daily_fitness,
)
from src.utils.metric_priority import resolve_for_scope

log = logging.getLogger(__name__)


def save_activity_core(conn: sqlite3.Connection, core_dict: dict) -> int:
    """activity_summaries UPSERT. Returns: row id."""
    return upsert_activity(conn, core_dict)


def save_metrics(
    conn: sqlite3.Connection,
    scope_type: str,
    scope_id: str | int,
    source: str,
    metrics: list,
) -> int:
    """MetricRecord 리스트 → metric_store batch UPSERT.

    MetricRecord (dataclass) 또는 dict 모두 허용.
    """
    dicts: list[dict] = []
    for m in metrics:
        if hasattr(m, "metric_name"):  # MetricRecord dataclass
            d: dict[str, Any] = {
                "metric_name": m.metric_name,
                "category": m.category,
                "provider": source,
                "numeric_value": m.numeric_value,
                "text_value": m.text_value,
                "json_value": m.json_value,
                "algorithm_version": m.algorithm_version,
                "confidence": m.confidence,
                "raw_name": m.raw_name,
                "parent_metric_id": m.parent_metric_id,
            }
        else:
            d = dict(m)
            d.setdefault("provider", source)
        dicts.append(d)
    return upsert_metrics_batch(conn, scope_type, str(scope_id), dicts)


def save_laps(conn: sqlite3.Connection, activity_id: int, laps: list[dict]) -> int:
    return upsert_laps_batch(conn, activity_id, laps)


def save_streams(
    conn: sqlite3.Connection, activity_id: int, rows: list[dict]
) -> int:
    return upsert_streams_batch(conn, activity_id, rows)


def save_best_efforts(
    conn: sqlite3.Connection, activity_id: int, efforts: list[dict]
) -> int:
    return upsert_best_efforts_batch(conn, activity_id, efforts)


def save_daily_wellness(
    conn: sqlite3.Connection, date_str: str, core: dict
) -> int:
    core["date"] = date_str
    return upsert_daily_wellness(conn, core)


def save_daily_fitness(
    conn: sqlite3.Connection, date_str: str, source: str, fitness: dict
) -> int:
    return upsert_daily_fitness(
        conn, date_str, source,
        ctl=fitness.get("ctl"),
        atl=fitness.get("atl"),
        tsb=fitness.get("tsb"),
        ramp_rate=fitness.get("ramp_rate"),
        vo2max=fitness.get("vo2max"),
    )


def resolve_primaries(
    conn: sqlite3.Connection, scope_type: str, scope_id: str | int
) -> int:
    return resolve_for_scope(conn, scope_type, str(scope_id))


def record_sync_job(conn: sqlite3.Connection, job_dict: dict):
    """SyncResult.to_sync_job_dict() 결과를 sync_jobs 테이블에 기록."""
    conn.execute(
        """
        INSERT INTO sync_jobs
            (id, source, job_type, from_date, to_date, status,
             total_items, completed_items, error_count, last_error, retry_after)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            status = excluded.status,
            completed_items = excluded.completed_items,
            error_count = excluded.error_count,
            last_error = excluded.last_error,
            retry_after = excluded.retry_after,
            updated_at = datetime('now')
        """,
        (
            job_dict["id"],
            job_dict["source"],
            job_dict["job_type"],
            job_dict.get("from_date"),
            job_dict.get("to_date"),
            job_dict["status"],
            job_dict.get("total_items"),
            job_dict.get("completed_items"),
            job_dict.get("error_count"),
            job_dict.get("last_error"),
            job_dict.get("retry_after"),
        ),
    )
