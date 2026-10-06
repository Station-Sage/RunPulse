"""스트림 meta 백필(U18e) — Garmin 은 payload 재추출로 meta 생성, 나머지는 기존 행 기준으로 meta 기록(없으면 unknown)."""
from __future__ import annotations

import sqlite3

from src.sync.reextract import reextract_laps_streams
from src.sync.stream_meta_store import save_stream_meta

_MISSING_SQL = ("SELECT s.activity_id, s.source, COUNT(*), MIN(s.elapsed_sec), MAX(s.elapsed_sec) "
                "FROM activity_streams s LEFT JOIN activity_stream_meta m "
                "ON m.activity_id = s.activity_id AND m.source = s.source "
                "WHERE m.activity_id IS NULL GROUP BY s.activity_id, s.source")


def backfill_stream_meta(conn: sqlite3.Connection, dry_run: bool = False) -> dict:
    """반환 {"garmin": reextract 통계, "strava_measured", "unknown", "targets": [activity_id...]}."""
    stats = {"garmin": reextract_laps_streams(conn, "garmin", dry_run=dry_run),
             "strava_measured": 0, "unknown": 0, "targets": []}
    for aid, source, n, lo, hi in conn.execute(_MISSING_SQL).fetchall():
        basis = "measured" if source == "strava" else "unknown"
        stats["strava_measured" if basis == "measured" else "unknown"] += 1
        stats["targets"].append(aid)
        if dry_run:
            continue
        span = float(hi - lo) if lo is not None and hi is not None and n > 1 else None
        save_stream_meta(conn, aid, source,
                         {"time_basis": basis, "time_key": "time" if basis == "measured" else None,
                          "sample_count": n, "span_sec": span, "median_dt_sec": span / (n - 1) if span else None}, n)
    if not dry_run:
        conn.commit()
    return stats
