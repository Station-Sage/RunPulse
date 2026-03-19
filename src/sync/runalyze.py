"""Runalyze 데이터 동기화 (API Token)."""

import sqlite3
from datetime import datetime, timedelta

from src.utils import api
from src.utils.dedup import assign_group_id


_BASE_URL = "https://runalyze.com/api/v1"


def _headers(config: dict) -> dict[str, str]:
    """Runalyze API 인증 헤더."""
    return {"token": config["runalyze"]["token"]}


def sync_activities(config: dict, conn: sqlite3.Connection, days: int) -> int:
    """Runalyze 활동 데이터를 가져와 DB에 저장.

    Args:
        config: 전체 설정 딕셔너리.
        conn: SQLite 연결.
        days: 가져올 일수.

    Returns:
        새로 저장된 활동 수.
    """
    headers = _headers(config)
    cutoff = datetime.now() - timedelta(days=days)

    activities = api.get(f"{_BASE_URL}/activities", headers=headers)
    count = 0

    for act in activities:
        source_id = str(act.get("id", ""))
        start_time = act.get("datetime", "")

        if not start_time:
            continue

        try:
            if datetime.fromisoformat(start_time) < cutoff:
                continue
        except ValueError:
            continue

        distance_km = (act.get("distance") or 0) / 1000
        duration_sec = int(act.get("s") or act.get("duration") or 0)
        avg_pace = round(duration_sec / distance_km) if distance_km > 0 else None

        try:
            cursor = conn.execute(
                """INSERT OR IGNORE INTO activities
                   (source, source_id, activity_type, start_time, distance_km,
                    duration_sec, avg_pace_sec_km, avg_hr, max_hr,
                    elevation_gain, calories, description)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    "runalyze", source_id, "running",
                    start_time, distance_km, duration_sec, avg_pace,
                    act.get("heart_rate_avg") or act.get("pulse_avg"),
                    act.get("heart_rate_max") or act.get("pulse_max"),
                    act.get("elevation"), act.get("calories"),
                    act.get("title"),
                ),
            )
        except sqlite3.Error as e:
            print(f"[runalyze] 활동 삽입 실패 {source_id}: {e}")
            continue

        if cursor.rowcount == 0:
            continue

        activity_id = cursor.lastrowid
        count += 1

        # 상세 지표
        try:
            detail = api.get(f"{_BASE_URL}/activities/{source_id}", headers=headers)
            metrics = {
                "effective_vo2max": detail.get("vo2max"),
                "vdot": detail.get("vdot"),
                "trimp": detail.get("trimp"),
            }
            for name, value in metrics.items():
                if value is not None:
                    conn.execute(
                        """INSERT INTO source_metrics
                           (activity_id, source, metric_name, metric_value)
                           VALUES (?, 'runalyze', ?, ?)""",
                        (activity_id, name, float(value)),
                    )
        except Exception as e:
            print(f"[runalyze] 상세 조회 실패 {source_id}: {e}")

        assign_group_id(conn, activity_id)

    conn.commit()
    return count
