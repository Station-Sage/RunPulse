"""Intervals.icu 선수 프로필 동기화."""

import json
import sqlite3
from datetime import datetime

from src.utils import api
from .intervals_auth import auth


def sync_athlete_profile(config: dict, conn: sqlite3.Connection) -> None:
    """Intervals.icu 선수 프로필 → athlete_profile 저장.

    Args:
        config: 전체 설정 딕셔너리.
        conn: SQLite 연결.
    """
    athlete_id = config["intervals"]["athlete_id"]
    _auth = auth(config)

    try:
        profile = api.get(
            f"https://intervals.icu/api/v1/athlete/{athlete_id}",
            auth=_auth,
        )
    except Exception as e:
        print(f"[intervals] 선수 프로필 조회 실패: {e}")
        return

    try:
        conn.execute(
            """INSERT INTO athlete_profile
               (source, source_athlete_id, firstname, lastname, city, country,
                sex, weight_kg, ftp, lthr, vo2max, profile_json, updated_at)
               VALUES ('intervals', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
               ON CONFLICT(source) DO UPDATE SET
                   source_athlete_id = excluded.source_athlete_id,
                   firstname = excluded.firstname,
                   lastname = excluded.lastname,
                   city = excluded.city,
                   country = excluded.country,
                   sex = excluded.sex,
                   weight_kg = excluded.weight_kg,
                   ftp = excluded.ftp,
                   lthr = excluded.lthr,
                   vo2max = excluded.vo2max,
                   profile_json = excluded.profile_json,
                   updated_at = datetime('now')""",
            (
                str(profile.get("id") or athlete_id),
                profile.get("firstname") or profile.get("name"),
                profile.get("lastname"),
                profile.get("city"),
                profile.get("country"),
                profile.get("sex"),
                profile.get("weight"),
                profile.get("ftp"),
                profile.get("lthr"),
                profile.get("vo2max"),
                json.dumps(profile, ensure_ascii=False),
            ),
        )
    except Exception as e:
        print(f"[intervals] 선수 프로필 저장 실패: {e}")


def sync_athlete_stats_snapshot(config: dict, conn: sqlite3.Connection) -> None:
    """Intervals.icu 누적 활동 통계 스냅샷 → athlete_stats 저장.

    DB의 intervals 활동 데이터를 집계하여 오늘 날짜 스냅샷 저장.
    """
    date_str = datetime.now().strftime("%Y-%m-%d")
    year_start = f"{datetime.now().year}-01-01"

    try:
        all_row = conn.execute(
            """SELECT COUNT(*), SUM(distance_km), SUM(duration_sec), SUM(elevation_gain)
               FROM activity_summaries WHERE source = 'intervals'"""
        ).fetchone()

        ytd_row = conn.execute(
            """SELECT COUNT(*), SUM(distance_km), SUM(duration_sec)
               FROM activity_summaries WHERE source = 'intervals' AND start_time >= ?""",
            (year_start,),
        ).fetchone()

        recent_row = conn.execute(
            """SELECT COUNT(*), SUM(distance_km)
               FROM activity_summaries WHERE source = 'intervals'
               AND start_time >= date('now', '-28 days')"""
        ).fetchone()

        conn.execute(
            """INSERT INTO athlete_stats
               (source, snapshot_date, all_run_count, all_run_distance_km,
                all_run_elapsed_sec, all_run_elevation_m,
                ytd_run_count, ytd_run_distance_km, ytd_run_elapsed_sec,
                recent_run_count, recent_run_distance_km, updated_at)
               VALUES ('intervals', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
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
                   updated_at = datetime('now')""",
            (
                date_str,
                all_row[0] or 0, all_row[1] or 0,
                all_row[2] or 0, all_row[3] or 0,
                ytd_row[0] or 0, ytd_row[1] or 0, ytd_row[2] or 0,
                recent_row[0] or 0, recent_row[1] or 0,
            ),
        )
    except Exception as e:
        print(f"[intervals] 통계 스냅샷 저장 실패: {e}")
