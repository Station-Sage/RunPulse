"""Intervals.icu 웰니스 / 피트니스 동기화."""

import sqlite3
from datetime import datetime, timedelta

from src.utils import api
from src.utils.db_helpers import upsert_metric
from src.utils.raw_payload import store_raw_payload as _store_rp

from .intervals_auth import base_url, auth


def _store_raw(
    conn: sqlite3.Connection,
    entity_type: str,
    entity_id: str,
    payload: dict,
) -> None:
    _store_rp(conn, "intervals", entity_type, entity_id, payload)


def sync_wellness(config: dict, conn: sqlite3.Connection, days: int) -> int:
    """Intervals.icu 웰니스/피트니스 데이터를 가져와 DB에 저장.

    CTL/ATL/TSB는 metric_store(scope=daily)에 저장 (ADR-005).
    수면/HRV 등은 daily_wellness 테이블에 저장.

    Args:
        config: 전체 설정 딕셔너리.
        conn: SQLite 연결.
        days: 가져올 일수.

    Returns:
        저장된 레코드 수.
    """
    _base = base_url(config)
    _auth = auth(config)
    oldest = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    newest = datetime.now().strftime("%Y-%m-%d")

    wellness_data = api.get(
        f"{_base}/wellness",
        params={"oldest": oldest, "newest": newest},
        auth=_auth,
    )
    count = 0

    for entry in wellness_data:
        date_str = entry.get("id", "")  # Intervals.icu wellness ID는 날짜
        if not date_str:
            continue

        _store_raw(conn, "wellness", date_str, entry)

        # 수면/HRV → daily_wellness (v0.3 스키마)
        try:
            conn.execute(
                """INSERT INTO daily_wellness
                   (date, sleep_score, sleep_duration_sec, hrv_last_night,
                    resting_hr, body_battery_high, avg_stress, steps, weight_kg)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(date) DO UPDATE SET
                       sleep_score = COALESCE(excluded.sleep_score, sleep_score),
                       sleep_duration_sec = COALESCE(excluded.sleep_duration_sec, sleep_duration_sec),
                       hrv_last_night = COALESCE(excluded.hrv_last_night, hrv_last_night),
                       resting_hr = COALESCE(excluded.resting_hr, resting_hr),
                       body_battery_high = COALESCE(excluded.body_battery_high, body_battery_high),
                       avg_stress = COALESCE(excluded.avg_stress, avg_stress),
                       steps = COALESCE(excluded.steps, steps),
                       weight_kg = COALESCE(excluded.weight_kg, weight_kg),
                       updated_at = datetime('now')""",
                (
                    date_str,
                    entry.get("sleepQuality"),
                    entry.get("sleepSecs"),
                    entry.get("hrv"),
                    entry.get("restingHR"),
                    entry.get("bodyBattery"),
                    entry.get("avgStress"),
                    entry.get("steps"),
                    entry.get("weight"),
                ),
            )
            count += 1
        except sqlite3.Error as e:
            print(f"[intervals] 웰니스 삽입 실패 {date_str}: {e}")

        # CTL/ATL/TSB → metric_store(scope=daily)
        ctl = entry.get("ctl")
        atl = entry.get("atl")
        tsb = entry.get("form")
        if tsb is None and ctl is not None and atl is not None:
            tsb = round(ctl - atl, 2)
        ramp_rate = entry.get("rampRate")

        for metric_name, val in [("ctl", ctl), ("atl", atl),
                                  ("tsb", tsb), ("ramp_rate", ramp_rate)]:
            if val is not None:
                upsert_metric(conn, "daily", date_str, metric_name, "intervals",
                              numeric_value=float(val), category="load")

    conn.commit()
    return count
