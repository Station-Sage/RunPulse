"""스키마 v21 — 예측 스냅샷(P7-PRED-63): 모델별 예측을 그날 값 그대로 보존해 대회 후 전향 평가한다.

mode 'live' = 동기화 직후 그날 예측(전향), 'retro' = 과거 시점 재계산(회고, in-sample). 평가·요약은 live 만 쓴다.
"""
from __future__ import annotations

import sqlite3

DDL_PREDICTION_SNAPSHOTS = """
CREATE TABLE IF NOT EXISTS prediction_snapshots (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at       TEXT DEFAULT (datetime('now')),
    as_of            TEXT NOT NULL,
    mode             TEXT NOT NULL DEFAULT 'live' CHECK(mode IN ('live', 'retro')),
    provider         TEXT NOT NULL,
    variant          TEXT,
    model_version    TEXT,
    distance_m       REAL NOT NULL,
    pred_s           REAL NOT NULL,
    low_s            REAL,
    high_s           REAL,
    confidence       REAL,
    inputs_json      TEXT,
    race_activity_id INTEGER,
    horizon_days     INTEGER,
    actual_s         REAL,
    residual_pct     REAL,
    covariates_json  TEXT,
    UNIQUE(as_of, mode, provider, distance_m)
);
CREATE INDEX IF NOT EXISTS idx_pred_snap_dist_asof ON prediction_snapshots(distance_m, as_of);
"""


def ensure_v21(conn: sqlite3.Connection) -> None:
    """v21 테이블을 멱등적으로 보장한다."""
    conn.executescript(DDL_PREDICTION_SNAPSHOTS)
