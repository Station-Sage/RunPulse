"""Intervals.icu 데이터 동기화 (Basic Auth) — 하위 모듈 wrapper.

하위 모듈:
  intervals_auth.py           — 인증, 연결 확인
  intervals_activity_sync.py  — 활동 동기화 (list/intervals/streams)
  intervals_wellness_sync.py  — 웰니스/피트니스 동기화
  intervals_athlete_sync.py   — 선수 프로필, 통계 스냅샷
"""

import sqlite3

# 하위 호환성을 위한 re-export
from .intervals_auth import (  # noqa: F401
    base_url as _base_url,
    auth as _auth,
    check_intervals_connection,
)
# v0.3: removed — use intervals_activity_sync.sync()
# v0.3: removed — use intervals_wellness_sync.sync()
from .intervals_athlete_sync import (  # noqa: F401
    sync_athlete_profile,
    sync_athlete_stats_snapshot,
)


def sync_intervals(
    config: dict,
    conn: sqlite3.Connection,
    days: int,
    from_date: str | None = None,
    to_date: str | None = None,
) -> dict:
    """Intervals.icu 전체 동기화: 활동 + 웰니스 + 선수 프로필.

    Args:
        config: 전체 설정 딕셔너리.
        conn: SQLite 연결.
        days: 가져올 일수.
        from_date: 기간 동기화 시작일.
        to_date: 기간 동기화 종료일.

    Returns:
        {"activities": N, "wellness": N, "profile": bool}
    """
    act_count = sync_activities(config, conn, days, from_date, to_date)
    well_count = sync_wellness(config, conn, days)

    try:
        sync_athlete_profile(config, conn)
        sync_athlete_stats_snapshot(config, conn)
    except Exception as e:
        print(f"[intervals] 선수 프로필 동기화 실패: {e}")

    conn.commit()
    return {"activities": act_count, "wellness": well_count, "profile": True}
