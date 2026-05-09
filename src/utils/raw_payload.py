"""source_payloads 저장/병합 유틸리티."""
from __future__ import annotations

import sqlite3


def store_raw_payload(
    conn: sqlite3.Connection,
    source: str,
    entity_type: str,
    entity_id: str,
    payload: dict,
    activity_id: int | None = None,
) -> None:
    """source_payloads에 payload 저장 (v0.3 테이블명)."""
    if not payload:
        return
    try:
        from src.utils.db_helpers import upsert_payload
        upsert_payload(conn, source, entity_type, entity_id, payload, activity_id=activity_id)
    except Exception as e:
        print(f"[raw_payload] 저장 실패 {source}/{entity_type}/{entity_id}: {e}")


def update_changed_fields(
    conn: sqlite3.Connection,
    source: str,
    source_id: str,
    updates: dict[str, object],
) -> int | None:
    """activity_summaries의 필드를 incoming 데이터와 비교하여 누락/변경 시 업데이트.

    COALESCE 방식과 달리 기존 값이 있어도 incoming 값이 다르면 업데이트한다.

    Args:
        conn: SQLite 연결.
        source: 소스명.
        source_id: 소스 고유 ID.
        updates: {컬럼명: 새값} — None 값은 무시.

    Returns:
        해당 레코드의 activity_summaries.id, 없으면 None.
    """
    non_null = {k: v for k, v in updates.items() if v is not None}
    if not non_null:
        row = conn.execute(
            "SELECT id FROM activity_summaries WHERE source = ? AND source_id = ?",
            (source, source_id),
        ).fetchone()
        return row[0] if row else None

    cols = list(non_null.keys())
    try:
        row = conn.execute(
            f"SELECT id, {', '.join(cols)} FROM activity_summaries "
            "WHERE source = ? AND source_id = ?",
            (source, source_id),
        ).fetchone()
    except sqlite3.OperationalError:
        # 컬럼명이 잘못된 경우 graceful fallback
        row = conn.execute(
            "SELECT id FROM activity_summaries WHERE source = ? AND source_id = ?",
            (source, source_id),
        ).fetchone()
        return row[0] if row else None

    if not row:
        return None

    activity_id = row[0]
    current = dict(zip(cols, row[1:]))

    to_update = {
        col: val
        for col, val in non_null.items()
        if current.get(col) is None or current.get(col) != val
    }
    if to_update:
        set_clause = ", ".join(f"{col} = ?" for col in to_update)
        conn.execute(
            f"UPDATE activity_summaries SET {set_clause} WHERE source = ? AND source_id = ?",
            (*to_update.values(), source, source_id),
        )
    return activity_id


def fill_null_columns(
    conn: sqlite3.Connection,
    source: str,
    source_id: str,
    updates: dict[str, object],
) -> int | None:
    """activity_summaries의 NULL 컬럼을 새 값으로 보완 업데이트.

    COALESCE를 사용하므로 기존에 값이 있으면 변경하지 않는다.

    Args:
        conn: SQLite 연결.
        source: 소스명.
        source_id: 소스 고유 ID.
        updates: {컬럼명: 새값} — None 값은 무시.

    Returns:
        해당 레코드의 activity_summaries.id, 없으면 None.
    """
    non_null = {k: v for k, v in updates.items() if v is not None}
    if non_null:
        set_clause = ", ".join(f"{col} = COALESCE({col}, ?)" for col in non_null)
        conn.execute(
            f"UPDATE activity_summaries SET {set_clause} WHERE source = ? AND source_id = ?",
            (*non_null.values(), source, source_id),
        )
    row = conn.execute(
        "SELECT id FROM activity_summaries WHERE source = ? AND source_id = ?",
        (source, source_id),
    ).fetchone()
    return row[0] if row else None
