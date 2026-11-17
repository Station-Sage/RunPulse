"""스키마 v43 — activity_streams 에 sample_idx 추가, 유니크 키를 (activity, source, elapsed_sec, sample_idx) 로 확장.

같은 초로 반올림되는 샘플이 INSERT OR IGNORE 로 유실되지 않게 한다. 테이블 재생성 방식, 멱등.
"""
from __future__ import annotations

import logging
import sqlite3

log = logging.getLogger(__name__)

_COLS = [
    "id", "activity_id", "source", "elapsed_sec", "distance_m", "heart_rate", "cadence",
    "power_watts", "altitude_m", "speed_ms", "latitude", "longitude", "grade_pct",
    "temperature_c", "created_at", "gap_speed_ms",
]

_DDL_NEW = """
CREATE TABLE activity_streams_v43 (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    activity_id     INTEGER NOT NULL,
    source          TEXT NOT NULL,
    elapsed_sec     INTEGER NOT NULL,
    sample_idx      INTEGER NOT NULL DEFAULT 0,
    distance_m      REAL,
    heart_rate      INTEGER,
    cadence         INTEGER,
    power_watts     REAL,
    altitude_m      REAL,
    speed_ms        REAL,
    latitude        REAL,
    longitude       REAL,
    grade_pct       REAL,
    temperature_c   REAL,
    created_at      TEXT DEFAULT (datetime('now')),
    gap_speed_ms    REAL,
    UNIQUE(activity_id, source, elapsed_sec, sample_idx)
)
"""


def ensure_v43(conn: sqlite3.Connection) -> None:
    """sample_idx 가 없는 기존 activity_streams 를 재생성한다(행 보존)."""
    cols = {r[1] for r in conn.execute("PRAGMA table_info(activity_streams)")}
    if not cols or "sample_idx" in cols:
        return
    check = conn.execute("PRAGMA integrity_check").fetchone()[0]
    if check != "ok":
        raise RuntimeError(f"v43 중단: integrity_check={check}")
    keep = [c for c in _COLS if c in cols]
    names = ", ".join(keep)
    conn.execute("DROP TABLE IF EXISTS activity_streams_v43")
    conn.execute(_DDL_NEW)
    conn.execute(f"INSERT INTO activity_streams_v43 ({names}) SELECT {names} FROM activity_streams")
    conn.execute("DROP TABLE activity_streams")
    conn.execute("ALTER TABLE activity_streams_v43 RENAME TO activity_streams")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_streams_activity ON activity_streams(activity_id, source)"
    )
    log.info("v43: activity_streams sample_idx 추가 (유니크 키 확장)")
