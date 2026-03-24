from __future__ import annotations

"""Garmin 선수 프로필/통계/기록 동기화 — athlete_profile, athlete_stats,
personal_records."""

import sqlite3
from datetime import date
from typing import TYPE_CHECKING

from src.sync.garmin_helpers import _store_raw_payload, _upsert_daily_detail_metric

if TYPE_CHECKING:
    from garminconnect import Garmin


def sync_athlete_profile(
    conn: sqlite3.Connection,
    client: "Garmin",
) -> None:
    """Garmin user_profile → athlete_profile 테이블 (소스별 1행 upsert)."""
    try:
        data = client.get_user_profile()
    except Exception as e:
        print(f"[garmin] user_profile 실패: {e}")
        return

    if not data:
        return

    today = date.today().isoformat()
    _store_raw_payload(conn, "user_profile", today, data)

    try:
        conn.execute(
            """INSERT INTO athlete_profile
               (source, username, first_name, last_name, city, country, profile_medium)
               VALUES ('garmin', ?, ?, ?, ?, ?, ?)
               ON CONFLICT(source) DO UPDATE SET
                   username = COALESCE(excluded.username, username),
                   first_name = COALESCE(excluded.first_name, first_name),
                   last_name = COALESCE(excluded.last_name, last_name),
                   city = COALESCE(excluded.city, city),
                   country = COALESCE(excluded.country, country),
                   profile_medium = COALESCE(excluded.profile_medium, profile_medium),
                   updated_at = datetime('now')""",
            (
                data.get("userName") or data.get("displayName"),
                data.get("firstName") or data.get("displayNameFormatted"),
                data.get("lastName"),
                data.get("city"),
                data.get("countryCode") or data.get("country"),
                data.get("profileImageUrlMedium") or data.get("profileImageUrl"),
            ),
        )
    except sqlite3.Error as e:
        print(f"[garmin] athlete_profile 저장 실패: {e}")


def sync_athlete_stats(
    conn: sqlite3.Connection,
    client: "Garmin",
    date_str: str | None = None,
) -> None:
    """Garmin stats (누적 통계 스냅샷) → athlete_stats 테이블."""
    today = date_str or date.today().isoformat()
    try:
        data = client.get_stats(today)
    except Exception as e:
        print(f"[garmin] stats 실패: {e}")
        return

    if not data:
        return

    _store_raw_payload(conn, "athlete_stats", today, data)

    def _km(m):
        return round(m / 1000, 3) if m is not None else None

    try:
        conn.execute(
            """INSERT INTO athlete_stats
               (source, snapshot_date, total_distance_km, total_elevation_m,
                total_moving_sec, total_activities, biggest_distance_km)
               VALUES ('garmin', ?, ?, ?, ?, ?, ?)
               ON CONFLICT(source, snapshot_date) DO UPDATE SET
                   total_distance_km = excluded.total_distance_km,
                   total_elevation_m = excluded.total_elevation_m,
                   total_moving_sec = excluded.total_moving_sec,
                   total_activities = excluded.total_activities,
                   biggest_distance_km = excluded.biggest_distance_km""",
            (
                today,
                _km(
                    data.get("totalDistanceMeters")
                    or data.get("totalDistanceInMeters")
                ),
                data.get("totalElevationGain"),
                (
                    data.get("totalDurationSeconds")
                    or data.get("totalMovingDurationSeconds")
                ),
                data.get("totalActivities"),
                _km(
                    data.get("longestActivity")
                    or data.get("maxDistanceMeters")
                ),
            ),
        )
    except sqlite3.Error as e:
        print(f"[garmin] athlete_stats 저장 실패: {e}")


def sync_athlete_personal_records(
    conn: sqlite3.Connection,
    client: "Garmin",
    date_str: str | None = None,
) -> int:
    """Garmin personal_records → activity_best_efforts + daily_detail_metrics.

    Returns:
        저장된 기록 수.
    """
    try:
        data = client.get_personal_records()
    except Exception as e:
        print(f"[garmin] personal_records 실패: {e}")
        return 0

    if not data:
        return 0

    today = date_str or date.today().isoformat()
    _store_raw_payload(conn, "personal_records", today, data)

    records = data if isinstance(data, list) else data.get("records", [])
    count = 0

    for rec in records:
        type_key = (
            rec.get("typeKey") or rec.get("prTypeName") or str(rec.get("typeId", ""))
        )
        value = rec.get("value") or rec.get("prValue")
        activity_id_src = rec.get("activityId")

        if not type_key or value is None:
            continue

        metric_name = f"pr_{type_key.lower().replace(' ', '_')}"
        try:
            _upsert_daily_detail_metric(
                conn, today, metric_name, metric_value=float(value)
            )
            count += 1
        except (TypeError, ValueError):
            continue

        # activity_best_efforts 연결 (garmin activity_id로 링크)
        if activity_id_src:
            try:
                row = conn.execute(
                    "SELECT id FROM activity_summaries "
                    "WHERE source = 'garmin' AND source_id = ?",
                    (str(activity_id_src),),
                ).fetchone()
                if row:
                    conn.execute(
                        """INSERT INTO activity_best_efforts
                           (activity_id, source, effort_name, elapsed_sec, pr_rank)
                           VALUES (?, 'garmin', ?, ?, 1)
                           ON CONFLICT(activity_id, source, effort_name) DO UPDATE SET
                               elapsed_sec = excluded.elapsed_sec,
                               pr_rank = 1""",
                        (row[0], type_key, float(value)),
                    )
            except sqlite3.Error:
                pass

    return count
