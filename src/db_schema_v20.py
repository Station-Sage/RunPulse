"""스키마 v20 — 예측 리뉴얼(REVIEW-07 r3) 데이터 보존용 컬럼·테이블 추가.

activity_laps: 경사보정 속도·고도 손실·기온·경과/이동 시간·컴플라이언스
activity_streams: 경사보정 속도
weather_cache: 체감온도·일사량
planned_workouts: 외부 시스템 식별·구조
session_outcomes: 세그먼트 매칭 결과
race_results: 대회 확인 입력(신규)
"""
from __future__ import annotations

import sqlite3

V20_COLUMNS: dict[str, list[tuple[str, str]]] = {
    "activity_laps": [
        ("gap_speed_ms", "REAL"),
        ("elevation_loss", "REAL"),
        ("avg_temperature_c", "REAL"),
        ("elapsed_duration_sec", "REAL"),
        ("moving_duration_sec", "REAL"),
        ("compliance_score", "REAL"),
        ("wkt_step_index", "INTEGER"),  # Garmin 워크아웃 단계 번호(계획 단계 ↔ 랩 매칭, P7-PRED-43)
    ],
    "activity_streams": [("gap_speed_ms", "REAL")],
    "weather_cache": [("feels_like_c", "REAL"), ("shortwave_wm2", "REAL")],
    "planned_workouts": [
        ("source_system", "TEXT"),      # runpulse | garmin | intervals
        ("external_id", "TEXT"),
        ("structure_json", "TEXT"),     # 단계 목록(P7-PRED-42 형식)
    ],
    "session_outcomes": [
        ("compliance_pct", "REAL"),
        ("segment_match_json", "TEXT"),
        ("source_compliance", "REAL"),
        ("source_system", "TEXT"),
    ],
}

DDL_RACE_RESULTS = """
CREATE TABLE IF NOT EXISTS race_results (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    activity_id       INTEGER NOT NULL UNIQUE,
    race_name         TEXT,
    distance_m        REAL NOT NULL,
    official_time_sec INTEGER,
    effort            TEXT NOT NULL CHECK(effort IN ('allout', 'paced', 'fun', 'dnf')),
    note              TEXT,
    confirmed_at      TEXT DEFAULT (datetime('now'))
);
"""


def ensure_v20(conn: sqlite3.Connection) -> None:
    """v20 컬럼·테이블을 멱등적으로 보장한다(존재하는 테이블에만 ALTER)."""
    for table, cols in V20_COLUMNS.items():
        existing = {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        if not existing:
            continue
        for name, typ in cols:
            if name not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {typ}")
    conn.execute(DDL_RACE_RESULTS)
    # matcher 의 ON CONFLICT(planned_id) 가 요구하는 유일 제약(없어서 session_outcomes 저장이 항상 실패했다)
    conn.execute("DELETE FROM session_outcomes WHERE id NOT IN (SELECT max(id) FROM session_outcomes GROUP BY planned_id) "
                 "AND planned_id IS NOT NULL")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_session_outcomes_planned ON session_outcomes(planned_id)")
