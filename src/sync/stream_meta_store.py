"""스트림 저장 + 시간축 meta 기록(U18b) — scaled 환산, stored_count(동일 초 중복 탈락 반영), UPSERT."""
from __future__ import annotations

import logging
import sqlite3

from src.sync.extractors.stream_time import stream_meta
from src.utils.db_helpers import upsert_streams_batch

log = logging.getLogger(__name__)

_SUMMARY_SQL = ("SELECT elapsed_time_sec, duration_sec, moving_time_sec "
                "FROM activity_summaries WHERE id = ?")


def summary_total_sec(conn: sqlite3.Connection, activity_id: int) -> float | None:
    """summary 시간(elapsed_time_sec → duration_sec → moving_time_sec 순 첫 양수)."""
    row = conn.execute(_SUMMARY_SQL, (activity_id,)).fetchone()
    for v in row or ():
        if v and v > 0:
            return float(v)
    return None


def _scale_times(rows: list[dict], total: float) -> None:
    """키가 없던 스트림: 샘플 순번을 summary 시간으로 비례 환산(0..total)."""
    n = len(rows)
    for i, r in enumerate(rows):
        r["elapsed_sec"] = int(round(total * i / (n - 1))) if n > 1 else 0


def save_stream_meta(conn: sqlite3.Connection, activity_id: int, source: str, meta: dict,
                     stored_count: int) -> None:
    try:
        conn.execute(
            """INSERT INTO activity_stream_meta (activity_id, source, time_basis, time_key, sample_count,
                   stored_count, span_sec, median_dt_sec, extracted_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
               ON CONFLICT(activity_id, source) DO UPDATE SET
                   time_basis=excluded.time_basis, time_key=excluded.time_key,
                   sample_count=excluded.sample_count, stored_count=excluded.stored_count,
                   span_sec=excluded.span_sec, median_dt_sec=excluded.median_dt_sec,
                   extracted_at=excluded.extracted_at""",
            (activity_id, source, meta["time_basis"], meta.get("time_key"), meta["sample_count"],
             stored_count, meta.get("span_sec"), meta.get("median_dt_sec")))
    except sqlite3.OperationalError as e:       # v30 이전 DB — meta 없이 동작(소비자는 폴백)
        log.debug("activity_stream_meta 기록 생략: %s", e)


def store_streams(conn: sqlite3.Connection, activity_id: int, rows: list[dict]) -> int:
    """스트림 행 저장 + meta 기록. rows 가 StreamRows 가 아니면(meta 없음) 저장만 한다."""
    if not rows:
        return 0
    meta = getattr(rows, "meta", None)
    if meta is None:
        return upsert_streams_batch(conn, activity_id, rows)
    source = rows[0].get("source", "")
    if any(r.get("elapsed_sec") is None for r in rows):
        total = summary_total_sec(conn, activity_id)
        if total is None:
            log.warning("스트림 시간키·summary 시간 모두 없음 — 저장 생략 (activity %s/%s)", source, activity_id)
            return 0
        rows = list(rows)
        _scale_times(rows, total)
        meta = {**stream_meta(rows, "scaled", None, meta["sample_count"])}
    upsert_streams_batch(conn, activity_id, rows)
    n = conn.execute("SELECT COUNT(*) FROM activity_streams WHERE activity_id=? AND source=?",
                     (activity_id, source)).fetchone()[0]
    save_stream_meta(conn, activity_id, source, meta, n)
    return n
