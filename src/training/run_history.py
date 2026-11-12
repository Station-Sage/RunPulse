"""커넥션 단위 러닝 거리 이력 캐시 — v_canonical_activities(윈도우 뷰, 조회당 ~8ms)를 요청당 1회만 읽는다.

플랜 일정 계산이 같은 뷰를 20여 번 훑던 것을 한 번의 로드 + 파이썬 집계로 줄인다.
쓰기(자기 커넥션 total_changes)나 다른 커넥션의 커밋(data_version)이 있으면 캐시를 버린다.
"""
from __future__ import annotations

import sqlite3
import threading
from datetime import date

RUN_TYPES = "('running','run','virtualrun','treadmill','highintensityintervaltraining')"

_LOCAL = threading.local()      # sqlite3.Connection 은 weakref 불가 → 스레드당 최근 1개만 보관


def _stamp(conn: sqlite3.Connection) -> tuple[int, int]:
    return conn.total_changes, conn.execute("PRAGMA data_version").fetchone()[0]


def run_rows(conn: sqlite3.Connection) -> list[tuple[str, float]]:
    """(YYYY-MM-DD, distance_m) 목록. distance_m 이 NULL 인 행은 제외."""
    stamp = _stamp(conn)
    hit = getattr(_LOCAL, "slot", None)
    if hit and hit[0] is conn and hit[1] == stamp:
        return hit[2]
    rows = [(r[0], float(r[1])) for r in conn.execute(
        f"SELECT DATE(start_time), distance_m FROM v_canonical_activities WHERE activity_type IN {RUN_TYPES} "
        "AND distance_m IS NOT NULL AND start_time IS NOT NULL")]
    _LOCAL.slot = (conn, stamp, rows)
    return rows


def window_distances(conn: sqlite3.Connection, start: date, end: date) -> list[float]:
    """start <= 날짜 < end 인 러닝 거리(m)."""
    s, e = start.isoformat(), end.isoformat()
    return [m for d, m in run_rows(conn) if d and s <= d < e]
