from __future__ import annotations

"""Garmin Connect 데이터 동기화 — 메인 진입점.

하위 모듈:
  garmin_auth.py             — 인증 (_login, check_garmin_connection)
  garmin_helpers.py          — 공통 헬퍼 (_store_raw_payload, _upsert_vo2max 등)
  garmin_activity_sync.py    — 활동 동기화 (sync_activities, _sync_activity_splits)
  garmin_wellness_sync.py    — 웰니스 동기화 (sync_wellness)
  garmin_api_extensions.py   — 활동 확장 API (streams, gear, exercise_sets)
  garmin_daily_extensions.py — 일별 확장 API (race_predictions, training_status 등)
  garmin_athlete_extensions.py — 선수 프로필/통계 (personal_records, stats)
"""

import sqlite3
import time
from datetime import datetime, timedelta

from src.sync.garmin_auth import (  # noqa: F401 (re-export)
    Garmin,
    GarminConnectTooManyRequestsError,
    _login,
    _tokenstore_path,
    check_garmin_connection,
)
from src.sync.garmin_helpers import (  # noqa: F401 (re-export)
    _handle_rate_limit,
    _store_daily_detail_metrics,
    _store_raw_payload,
    _upsert_daily_detail_metric,
    _upsert_vo2max,
)
from src.sync.garmin_activity_sync import sync_activities, _sync_activity_splits  # noqa: F401
from src.sync.garmin_wellness_sync import sync_wellness  # noqa: F401
from src.sync.garmin_daily_extensions import (
    sync_daily_race_predictions,
    sync_daily_training_status,
    sync_daily_fitness_metrics,
    sync_daily_user_summary,
    sync_daily_heart_rates,
    sync_daily_all_day_stress,
    sync_daily_body_battery_events,
    sync_daily_hydration,
    sync_daily_weigh_ins,
    sync_daily_running_tolerance,
)
from src.sync.garmin_athlete_extensions import (
    sync_athlete_profile,
    sync_athlete_stats,
    sync_athlete_personal_records,
)


def sync_daily_extensions(
    config: dict,
    conn: sqlite3.Connection,
    days: int,
    client: "Garmin | None" = None,
) -> int:
    """일별 확장 API (race_predictions, training_status, fitness_metrics 등) 동기화.

    Returns:
        처리된 날 수.
    """
    if client is None:
        client = _login(config)

    today = datetime.now().date()
    count = 0
    for i in range(days):
        date_str = (today - timedelta(days=i)).isoformat()
        try:
            time.sleep(2)
            sync_daily_user_summary(conn, client, date_str)
        except Exception as e:
            print(f"[garmin] user_summary 확장 실패 {date_str}: {e}")

        try:
            time.sleep(2)
            sync_daily_training_status(conn, client, date_str)
        except Exception as e:
            print(f"[garmin] training_status 확장 실패 {date_str}: {e}")

        try:
            time.sleep(2)
            sync_daily_fitness_metrics(conn, client, date_str)
        except Exception as e:
            print(f"[garmin] fitness_metrics 확장 실패 {date_str}: {e}")

        try:
            time.sleep(2)
            sync_daily_heart_rates(conn, client, date_str)
        except Exception as e:
            print(f"[garmin] heart_rates 확장 실패 {date_str}: {e}")

        try:
            time.sleep(2)
            sync_daily_all_day_stress(conn, client, date_str)
        except Exception as e:
            print(f"[garmin] all_day_stress 확장 실패 {date_str}: {e}")

        try:
            time.sleep(2)
            sync_daily_body_battery_events(conn, client, date_str)
        except Exception as e:
            print(f"[garmin] body_battery_events 확장 실패 {date_str}: {e}")

        try:
            time.sleep(2)
            sync_daily_hydration(conn, client, date_str)
        except Exception as e:
            print(f"[garmin] hydration 확장 실패 {date_str}: {e}")

        try:
            time.sleep(2)
            sync_daily_weigh_ins(conn, client, date_str)
        except Exception as e:
            print(f"[garmin] weigh_ins 확장 실패 {date_str}: {e}")

        try:
            time.sleep(2)
            sync_daily_running_tolerance(conn, client, date_str)
        except Exception as e:
            print(f"[garmin] running_tolerance 확장 실패 {date_str}: {e}")

        count += 1

    # race_predictions는 날짜 무관 (최신 1건) — 첫날에만 호출
    if days > 0:
        try:
            time.sleep(2)
            sync_daily_race_predictions(conn, client, today.isoformat())
        except Exception as e:
            print(f"[garmin] race_predictions 확장 실패: {e}")

    conn.commit()
    return count


def sync_athlete_extensions(
    config: dict,
    conn: sqlite3.Connection,
    client: "Garmin | None" = None,
) -> None:
    """선수 프로필/통계/기록 동기화 (전체 동기화 시 1회 실행)."""
    if client is None:
        client = _login(config)

    try:
        sync_athlete_profile(conn, client)
    except Exception as e:
        print(f"[garmin] athlete_profile 실패: {e}")

    try:
        time.sleep(2)
        sync_athlete_stats(conn, client)
    except Exception as e:
        print(f"[garmin] athlete_stats 실패: {e}")

    try:
        time.sleep(2)
        sync_athlete_personal_records(conn, client)
    except Exception as e:
        print(f"[garmin] personal_records 실패: {e}")

    conn.commit()


def sync_garmin(config: dict, conn: sqlite3.Connection, days: int) -> dict:
    """Garmin 전체 동기화 (활동 + 웰니스 + 일별 확장 + 선수 데이터).

    Args:
        config: 전체 설정 딕셔너리.
        conn: SQLite 연결.
        days: 가져올 일수.

    Returns:
        {"activity_summaries": 저장 수, "wellness": 저장 수, "daily_ext": 처리 일수}
    """
    client = _login(config)
    act_count = sync_activities(config, conn, days, client=client)
    well_count = sync_wellness(config, conn, days, client=client)
    daily_count = sync_daily_extensions(config, conn, days, client=client)
    sync_athlete_extensions(config, conn, client=client)
    return {
        "activity_summaries": act_count,
        "wellness": well_count,
        "daily_ext": daily_count,
    }
