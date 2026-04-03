"""Strava 데이터 동기화 (OAuth2) — 하위 모듈 wrapper.

하위 모듈:
  strava_auth.py         — 토큰 관리, 연결 확인
  strava_activity_sync.py — 활동 동기화 (list/detail/streams/laps/best_efforts)
  strava_athlete_sync.py  — 선수 프로필, 통계, 기어
"""

import sqlite3

# 하위 호환성을 위한 re-export
from .strava_auth import (  # noqa: F401
    _BASE_URL,
    refresh_token as _refresh_token,
    check_strava_connection,
)
# v0.3: removed — use strava_activity_sync.sync()
from .strava_athlete_sync import (  # noqa: F401
    sync_athlete_profile,
    sync_athlete_stats,
    sync_gear,
    sync_athlete_and_gear,
)

from src.utils.sync_state import mark_finished


def sync_strava(
    config: dict,
    conn: sqlite3.Connection,
    days: int,
    from_date: str | None = None,
    to_date: str | None = None,
    bg_mode: bool = False,
) -> dict:
    """Strava 전체 동기화: 활동 + 선수 프로필 + 통계 + 기어.

    Args:
        config: 전체 설정 딕셔너리.
        conn: SQLite 연결.
        days: 가져올 일수.
        from_date: 기간 동기화 시작일.
        to_date: 기간 동기화 종료일.
        bg_mode: True이면 mark_finished 호출 생략.

    Returns:
        {"activities": N, "profile": bool, "stats": bool, "gear": int}
    """
    from .strava_auth import refresh_token

    token = refresh_token(config)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. 활동 동기화
    act_count = sync_activities(config, conn, days, from_date, to_date, bg_mode=True)

    # 2. 선수 프로필 + 통계 + 기어
    try:
        sync_athlete_and_gear(config, conn, headers)
    except Exception as e:
        print(f"[strava] 선수/기어 동기화 실패: {e}")

    conn.commit()
    if not bg_mode:
        mark_finished("strava", count=act_count)

    return {"activities": act_count, "profile": True, "stats": True}
