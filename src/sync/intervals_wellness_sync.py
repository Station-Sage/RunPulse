"""Intervals.icu 웰니스 / 피트니스 동기화."""

import sqlite3
from datetime import datetime, timedelta

from src.utils import api
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

    CTL/ATL/TSB는 daily_fitness 테이블에 저장 (일별 피트니스 추적).
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

        # 수면/HRV → daily_wellness
        try:
            conn.execute(
                """INSERT OR REPLACE INTO daily_wellness
                   (date, source, sleep_score, sleep_hours, hrv_value, hrv_sdnn,
                    resting_hr, avg_sleeping_hr, readiness_score,
                    fatigue, mood, motivation, steps, weight_kg)
                   VALUES (?, 'intervals', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    date_str,
                    entry.get("sleepQuality"),
                    entry.get("sleepSecs", 0) / 3600 if entry.get("sleepSecs") else None,
                    entry.get("hrv"),
                    entry.get("hrvSDNN"),
                    entry.get("restingHR"),
                    entry.get("avgSleepingHR"),
                    entry.get("readiness"),
                    entry.get("fatigue"),
                    entry.get("mood"),
                    entry.get("motivation"),
                    entry.get("steps"),
                    entry.get("weight"),
                ),
            )
            count += 1
        except sqlite3.Error as e:
            print(f"[intervals] 웰니스 삽입 실패 {date_str}: {e}")

        # CTL/ATL/TSB → daily_fitness
        ctl = entry.get("ctl")
        atl = entry.get("atl")
        tsb = entry.get("form")
        if tsb is None and ctl is not None and atl is not None:
            tsb = round(ctl - atl, 2)
        ramp_rate = entry.get("rampRate")

        if any(v is not None for v in [ctl, atl, tsb]):
            try:
                conn.execute(
                    """INSERT INTO daily_fitness (date, source, ctl, atl, tsb, ramp_rate)
                       VALUES (?, 'intervals', ?, ?, ?, ?)
                       ON CONFLICT(date, source) DO UPDATE SET
                           ctl = COALESCE(excluded.ctl, ctl),
                           atl = COALESCE(excluded.atl, atl),
                           tsb = COALESCE(excluded.tsb, tsb),
                           ramp_rate = COALESCE(excluded.ramp_rate, ramp_rate),
                           updated_at = datetime('now')""",
                    (date_str, ctl, atl, tsb, ramp_rate),
                )
            except sqlite3.OperationalError:
                pass
            except sqlite3.Error as e:
                print(f"[intervals] daily_fitness 삽입 실패 {date_str}: {e}")

    conn.commit()
    return count
