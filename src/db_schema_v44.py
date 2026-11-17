"""스키마 v44 — Garmin 러닝 다이내믹스·스트림 보조 지표 컬럼 추가(REVIEW-10 S-12·S-13).

activity_streams: 지면접촉시간·수직진동·보폭·수직비율·바디배터리·호흡수
activity_laps: 평균 지면접촉시간·수직진동·보폭·수직비율·정규화 파워·평균 호흡수
단위는 Garmin 원본 그대로(ms·cm·cm·%). 가산 ALTER, 멱등.
"""
from __future__ import annotations

import sqlite3

V44_COLUMNS: dict[str, list[tuple[str, str]]] = {
    "activity_streams": [
        ("ground_contact_ms", "REAL"),
        ("vertical_osc_cm", "REAL"),
        ("stride_length_cm", "REAL"),
        ("vertical_ratio_pct", "REAL"),
        ("body_battery", "REAL"),
        ("respiration_rate", "REAL"),
    ],
    "activity_laps": [
        ("avg_ground_contact_ms", "REAL"),
        ("avg_vertical_osc_cm", "REAL"),
        ("avg_stride_length_cm", "REAL"),
        ("avg_vertical_ratio_pct", "REAL"),
        ("normalized_power", "REAL"),
        ("avg_respiration_rate", "REAL"),
    ],
}


def ensure_v44(conn: sqlite3.Connection) -> None:
    """존재하는 테이블에만 누락 컬럼을 추가한다."""
    for table, cols in V44_COLUMNS.items():
        existing = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
        if not existing:
            continue
        for name, typ in cols:
            if name not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {typ}")
