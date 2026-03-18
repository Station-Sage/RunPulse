"""Intervals.icu 데이터 동기화 (Basic Auth)."""

import sqlite3
from datetime import datetime, timedelta

from src.utils import api
from src.utils.dedup import assign_group_id


def _base_url(config: dict) -> str:
    """Intervals.icu API base URL."""
    athlete_id = config["intervals"]["athlete_id"]
    return f"https://intervals.icu/api/v1/athlete/{athlete_id}"


def _auth(config: dict) -> tuple[str, str]:
    """Basic Auth 튜플 (API_KEY, api_key)."""
    return ("API_KEY", config["intervals"]["api_key"])


def sync_activities(config: dict, conn: sqlite3.Connection, days: int) -> int:
    """Intervals.icu 활동 데이터를 가져와 DB에 저장.

    Args:
        config: 전체 설정 딕셔너리.
        conn: SQLite 연결.
        days: 가져올 일수.

    Returns:
        새로 저장된 활동 수.
    """
    base = _base_url(config)
    auth = _auth(config)
    oldest = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    newest = datetime.now().strftime("%Y-%m-%d")

    activities = api.get(
        f"{base}/activities",
        params={"oldest": oldest, "newest": newest},
        auth=auth,
    )
    count = 0

    for act in activities:
        source_id = str(act.get("id", ""))
        distance_km = (act.get("distance") or 0) / 1000
        duration_sec = int(act.get("moving_time") or 0)
        avg_pace = round(duration_sec / distance_km) if distance_km > 0 else None
        start_time = act.get("start_date_local", "")

        try:
            cursor = conn.execute(
                """INSERT OR IGNORE INTO activities
                   (source, source_id, activity_type, start_time, distance_km,
                    duration_sec, avg_pace_sec_km, avg_hr, max_hr, avg_cadence,
                    elevation_gain, calories, description)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    "intervals", source_id,
                    act.get("type", "Run").lower(),
                    start_time, distance_km, duration_sec, avg_pace,
                    act.get("average_heartrate"), act.get("max_heartrate"),
                    act.get("average_cadence"),
                    act.get("total_elevation_gain"), act.get("calories"),
                    act.get("name"),
                ),
            )
        except sqlite3.Error as e:
            print(f"[intervals] 활동 삽입 실패 {source_id}: {e}")
            continue

        if cursor.rowcount == 0:
            continue

        activity_id = cursor.lastrowid
        count += 1

        # 소스 고유 지표
        metrics = {
            "icu_training_load": act.get("icu_training_load"),
            "icu_intensity": act.get("icu_intensity"),
            "icu_hrss": act.get("icu_hrss"),
        }
        for name, value in metrics.items():
            if value is not None:
                try:
                    conn.execute(
                        """INSERT INTO source_metrics
                           (activity_id, source, metric_name, metric_value)
                           VALUES (?, 'intervals', ?, ?)""",
                        (activity_id, name, float(value)),
                    )
                except sqlite3.Error:
                    pass

        assign_group_id(conn, activity_id)

    conn.commit()
    return count


def sync_wellness(config: dict, conn: sqlite3.Connection, days: int) -> int:
    """Intervals.icu 웰니스/피트니스 데이터를 가져와 DB에 저장.

    Args:
        config: 전체 설정 딕셔너리.
        conn: SQLite 연결.
        days: 가져올 일수.

    Returns:
        저장된 레코드 수.
    """
    base = _base_url(config)
    auth = _auth(config)
    oldest = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    newest = datetime.now().strftime("%Y-%m-%d")

    wellness_data = api.get(
        f"{base}/wellness",
        params={"oldest": oldest, "newest": newest},
        auth=auth,
    )
    count = 0

    for entry in wellness_data:
        date_str = entry.get("id", "")  # Intervals.icu wellness ID는 날짜
        if not date_str:
            continue

        try:
            conn.execute(
                """INSERT OR REPLACE INTO daily_wellness
                   (date, source, sleep_score, sleep_hours, hrv_value,
                    resting_hr, readiness_score)
                   VALUES (?, 'intervals', ?, ?, ?, ?, ?)""",
                (
                    date_str,
                    entry.get("sleepQuality"),
                    entry.get("sleepSecs", 0) / 3600 if entry.get("sleepSecs") else None,
                    entry.get("hrv"),
                    entry.get("restingHR"),
                    entry.get("readiness"),
                ),
            )
            count += 1
        except sqlite3.Error as e:
            print(f"[intervals] 웰니스 삽입 실패 {date_str}: {e}")

        # CTL/ATL/TSB를 source_metrics에 저장 (날짜 기반이지만 피트니스 추적용)
        ctl = entry.get("ctl")
        atl = entry.get("atl")
        if ctl is not None or atl is not None:
            # 가장 최근 활동에 연결하거나 별도 저장
            # 여기서는 wellness 날짜에 해당하는 활동이 있으면 연결
            row = conn.execute(
                "SELECT id FROM activities WHERE source='intervals' AND date(start_time)=?",
                (date_str,),
            ).fetchone()
            if row:
                for name, value in [("ctl", ctl), ("atl", atl), ("tsb", (ctl or 0) - (atl or 0))]:
                    if value is not None:
                        try:
                            conn.execute(
                                """INSERT OR REPLACE INTO source_metrics
                                   (activity_id, source, metric_name, metric_value)
                                   VALUES (?, 'intervals', ?, ?)""",
                                (row[0], name, float(value)),
                            )
                        except sqlite3.Error:
                            pass

    conn.commit()
    return count
