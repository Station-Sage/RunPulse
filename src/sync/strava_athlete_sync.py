"""Strava 선수 프로필, 통계, 기어 동기화."""

import json
import sqlite3
from datetime import datetime

from src.utils import api
from .strava_auth import _BASE_URL


def sync_athlete_profile(conn: sqlite3.Connection, headers: dict) -> None:
    """Strava 선수 프로필 → athlete_profile 저장.

    Args:
        conn: SQLite 연결.
        headers: Authorization 헤더.
    """
    try:
        athlete = api.get(f"{_BASE_URL}/athlete", headers=headers)
    except Exception as e:
        print(f"[strava] 선수 프로필 조회 실패: {e}")
        return

    try:
        conn.execute(
            """INSERT INTO athlete_profile
               (source, source_athlete_id, firstname, lastname, city, country,
                sex, weight_kg, ftp, profile_json, updated_at)
               VALUES ('strava', ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
               ON CONFLICT(source) DO UPDATE SET
                   source_athlete_id = excluded.source_athlete_id,
                   firstname = excluded.firstname,
                   lastname = excluded.lastname,
                   city = excluded.city,
                   country = excluded.country,
                   sex = excluded.sex,
                   weight_kg = excluded.weight_kg,
                   ftp = excluded.ftp,
                   profile_json = excluded.profile_json,
                   updated_at = datetime('now')""",
            (
                str(athlete.get("id", "")),
                athlete.get("firstname"),
                athlete.get("lastname"),
                athlete.get("city"),
                athlete.get("country"),
                athlete.get("sex"),
                athlete.get("weight"),
                athlete.get("ftp"),
                json.dumps(athlete, ensure_ascii=False),
            ),
        )
    except Exception as e:
        print(f"[strava] 선수 프로필 저장 실패: {e}")


def sync_athlete_stats(
    conn: sqlite3.Connection,
    athlete_id: int,
    headers: dict,
    date_str: str | None = None,
) -> None:
    """Strava 선수 통계 스냅샷 → athlete_stats 저장.

    Args:
        conn: SQLite 연결.
        athlete_id: Strava athlete ID.
        headers: Authorization 헤더.
        date_str: 스냅샷 날짜 (YYYY-MM-DD). None이면 오늘.
    """
    date_str = date_str or datetime.now().strftime("%Y-%m-%d")
    try:
        stats = api.get(f"{_BASE_URL}/athletes/{athlete_id}/stats", headers=headers)
    except Exception as e:
        print(f"[strava] 선수 통계 조회 실패: {e}")
        return

    recent = stats.get("recent_run_totals") or {}
    ytd = stats.get("ytd_run_totals") or {}
    all_ = stats.get("all_run_totals") or {}

    try:
        conn.execute(
            """INSERT INTO athlete_stats
               (source, snapshot_date, all_run_count, all_run_distance_km,
                all_run_elapsed_sec, all_run_elevation_m,
                ytd_run_count, ytd_run_distance_km, ytd_run_elapsed_sec,
                recent_run_count, recent_run_distance_km, stats_json, updated_at)
               VALUES ('strava', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
               ON CONFLICT(source, snapshot_date) DO UPDATE SET
                   all_run_count = excluded.all_run_count,
                   all_run_distance_km = excluded.all_run_distance_km,
                   all_run_elapsed_sec = excluded.all_run_elapsed_sec,
                   all_run_elevation_m = excluded.all_run_elevation_m,
                   ytd_run_count = excluded.ytd_run_count,
                   ytd_run_distance_km = excluded.ytd_run_distance_km,
                   ytd_run_elapsed_sec = excluded.ytd_run_elapsed_sec,
                   recent_run_count = excluded.recent_run_count,
                   recent_run_distance_km = excluded.recent_run_distance_km,
                   stats_json = excluded.stats_json,
                   updated_at = datetime('now')""",
            (
                date_str,
                all_.get("count"),
                (all_.get("distance") or 0) / 1000,
                all_.get("elapsed_time"),
                all_.get("elevation_gain"),
                ytd.get("count"),
                (ytd.get("distance") or 0) / 1000,
                ytd.get("elapsed_time"),
                recent.get("count"),
                (recent.get("distance") or 0) / 1000,
                json.dumps(stats, ensure_ascii=False),
            ),
        )
    except Exception as e:
        print(f"[strava] 선수 통계 저장 실패: {e}")


def sync_gear(conn: sqlite3.Connection, gear_id: str, headers: dict) -> None:
    """Strava 기어(신발/자전거) 상세 → gear 저장.

    Args:
        conn: SQLite 연결.
        gear_id: Strava gear ID (예: "g12345").
        headers: Authorization 헤더.
    """
    try:
        gear = api.get(f"{_BASE_URL}/gear/{gear_id}", headers=headers)
    except Exception as e:
        print(f"[strava] 기어 조회 실패 {gear_id}: {e}")
        return

    try:
        conn.execute(
            """INSERT INTO gear
               (source, source_gear_id, name, brand, model, distance_m,
                retired, gear_type, gear_json, updated_at)
               VALUES ('strava', ?, ?, ?, ?, ?, ?, 'shoes', ?, datetime('now'))
               ON CONFLICT(source, source_gear_id) DO UPDATE SET
                   name = excluded.name,
                   brand = excluded.brand,
                   model = excluded.model,
                   distance_m = excluded.distance_m,
                   retired = excluded.retired,
                   gear_json = excluded.gear_json,
                   updated_at = datetime('now')""",
            (
                gear_id,
                gear.get("name"),
                gear.get("brand_name"),
                gear.get("model_name"),
                gear.get("distance"),
                int(bool(gear.get("retired", False))),
                json.dumps(gear, ensure_ascii=False),
            ),
        )
    except Exception as e:
        print(f"[strava] 기어 저장 실패 {gear_id}: {e}")


def sync_athlete_and_gear(config: dict, conn: sqlite3.Connection, headers: dict) -> None:
    """선수 프로필 + 통계 + 신규 기어 일괄 동기화.

    Args:
        config: 전체 설정 딕셔너리.
        conn: SQLite 연결.
        headers: Authorization 헤더.
    """
    # 1. 선수 프로필
    sync_athlete_profile(conn, headers)

    # 2. 선수 통계 (athlete_id 필요)
    athlete_id = config.get("strava", {}).get("athlete_id")
    if athlete_id:
        sync_athlete_stats(conn, int(athlete_id), headers)

    # 3. 미수집 기어 동기화 (activity_summaries에 gear_id가 있지만 gear 테이블에 없는 것)
    try:
        gear_ids = conn.execute(
            """SELECT DISTINCT strava_gear_id FROM activity_summaries
               WHERE source = 'strava' AND strava_gear_id IS NOT NULL
               AND strava_gear_id NOT IN (SELECT source_gear_id FROM gear WHERE source = 'strava')"""
        ).fetchall()
        for (gid,) in gear_ids:
            sync_gear(conn, gid, headers)
    except Exception as e:
        print(f"[strava] 기어 목록 조회 실패: {e}")
