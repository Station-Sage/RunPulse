"""Intervals.icu 데이터 동기화 (Basic Auth)."""

import json
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

        # 활동 단위 고유 지표 (per-activity → source_metrics 유지)
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

        # TODO: HR Zone Distribution 수집
        # Intervals.icu activity detail에 hr_zones 필드가 있을 수 있음
        # 현재 API 응답 구조 확인 필요. 확인 후 구현 예정.
        # hr_zones = act.get("hr_zones")  # 예상 필드명
        # if hr_zones:
        #     conn.execute(INSERT INTO source_metrics ... 'hr_zone_distribution', metric_json=json.dumps(hr_zones))

        assign_group_id(conn, activity_id)

    conn.commit()
    return count


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

        # 수면/HRV → daily_wellness
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

        # CTL/ATL/TSB → daily_fitness (일별 피트니스 지표)
        ctl = entry.get("ctl")
        atl = entry.get("atl")
        # Intervals.icu는 form = CTL - ATL (TSB)
        tsb = entry.get("form")
        if tsb is None and ctl is not None and atl is not None:
            tsb = round(ctl - atl, 2)
        ramp_rate = entry.get("rampRate")

        if any(v is not None for v in [ctl, atl, tsb]):
            try:
                conn.execute("""
                    INSERT INTO daily_fitness (date, source, ctl, atl, tsb, ramp_rate)
                    VALUES (?, 'intervals', ?, ?, ?, ?)
                    ON CONFLICT(date, source) DO UPDATE SET
                        ctl = COALESCE(excluded.ctl, ctl),
                        atl = COALESCE(excluded.atl, atl),
                        tsb = COALESCE(excluded.tsb, tsb),
                        ramp_rate = COALESCE(excluded.ramp_rate, ramp_rate),
                        updated_at = datetime('now')
                """, (date_str, ctl, atl, tsb, ramp_rate))
            except sqlite3.OperationalError:
                pass  # daily_fitness 테이블 미생성 환경 (graceful)
            except sqlite3.Error as e:
                print(f"[intervals] daily_fitness 삽입 실패 {date_str}: {e}")

    conn.commit()
    return count
