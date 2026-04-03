"""Raw payload 저장 — db_helpers.upsert_payload()의 Sync-friendly 래퍼."""

from __future__ import annotations

import sqlite3
from src.utils.db_helpers import upsert_payload


def upsert_raw_payload(
    conn: sqlite3.Connection,
    source: str,
    entity_type: str,
    entity_id: str,
    payload: dict,
    endpoint: str = None,
    entity_date: str = None,
    activity_id: int = None,
    parser_version: str = "1.0",
) -> bool:
    """source_payloads에 raw JSON 저장.

    Returns: True if payload was new or changed, False if identical (skip).
    """
    _row_id, is_new = upsert_payload(
        conn, source, entity_type, entity_id, payload,
        entity_date=entity_date,
        activity_id=activity_id,
        endpoint=endpoint,
        parser_version=parser_version,
    )
    return is_new


def update_raw_activity_id(
    conn: sqlite3.Connection,
    source: str,
    entity_type: str,
    entity_id: str,
    activity_id: int,
):
    """raw payload에 activity_summaries.id 역참조 설정."""
    conn.execute(
        "UPDATE source_payloads SET activity_id = ? "
        "WHERE source = ? AND entity_type = ? AND entity_id = ?",
        (activity_id, source, entity_type, entity_id),
    )
