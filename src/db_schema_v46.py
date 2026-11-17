"""스키마 v46 — wellness_series: 일중 웰니스 시계열 저장소(REVIEW-10 A6).

HRV 5분 readings·수면 단계·수면 중 HR·Body Battery·스트레스·일중 HR·SpO2·호흡을
(date, source, kind, ts) 단위로 보관한다. ts 는 UTC epoch 초. 가산 테이블, 멱등.
"""
from __future__ import annotations

import sqlite3


def ensure_v46(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS wellness_series (
            date   TEXT NOT NULL,
            source TEXT NOT NULL,
            kind   TEXT NOT NULL,
            ts     INTEGER NOT NULL,
            value  REAL,
            meta   TEXT,
            PRIMARY KEY (date, source, kind, ts)
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_wellness_series_kind_ts "
        "ON wellness_series(kind, ts)"
    )
