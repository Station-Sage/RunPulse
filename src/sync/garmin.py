"""Garmin Connect 데이터 동기화."""

import sqlite3
import time
from datetime import datetime, timedelta

from garminconnect import Garmin

from src.utils.dedup import assign_group_id


def _login(config: dict) -> Garmin:
    """Garmin Connect 로그인."""
    garmin_cfg = config["garmin"]
    client = Garmin(garmin_cfg["email"], garmin_cfg["password"])
    client.login()
    return client


def sync_activities(config: dict, conn: sqlite3.Connection, days: int) -> int:
    """Garmin 활동 데이터를 가져와 DB에 저장.

    Args:
        config: 전체 설정 딕셔너리.
        conn: SQLite 연결.
        days: 가져올 일수.

    Returns:
        새로 저장된 활동 수.
    """
    client = _login(config)
    activities = client.get_activities(0, days * 3)
    cutoff = datetime.now() - timedelta(days=days)
    count = 0

    for act in activities:
        start_time = act.get("startTimeLocal", "")
        if not start_time:
            continue

        try:
            if datetime.fromisoformat(start_time) < cutoff:
                continue
        except ValueError:
            continue

        source_id = str(act.get("activityId", ""))
        distance_km = (act.get("distance") or 0) / 1000
        duration_sec = int(act.get("duration") or 0)
        avg_pace = round(duration_sec / distance_km) if distance_km > 0 else None

        try:
            cursor = conn.execute(
                """INSERT OR IGNORE INTO activities
                   (source, source_id, activity_type, start_time, distance_km,
                    duration_sec, avg_pace_sec_km, avg_hr, max_hr, avg_cadence,
                    elevation_gain, calories, description)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    "garmin", source_id,
                    act.get("activityType", {}).get("typeKey", "running"),
                    start_time, distance_km, duration_sec, avg_pace,
                    act.get("averageHR"), act.get("maxHR"),
                    act.get("averageRunningCadenceInStepsPerMinute"),
                    act.get("elevationGain"), act.get("calories"),
                    act.get("activityName"),
                ),
            )
        except sqlite3.Error as e:
            print(f"[garmin] 활동 삽입 실패 {source_id}: {e}")
            continue

        if cursor.rowcount == 0:
            continue  # 이미 존재

        activity_id = cursor.lastrowid
        count += 1

        # 상세 지표 가져오기
        try:
            time.sleep(2)
            detail = client.get_activity(int(source_id))
            metrics = {
                "training_effect": detail.get("aerobicTrainingEffect"),
                "training_load": detail.get("activityTrainingLoad"),
                "vo2max": detail.get("vO2MaxValue"),
            }
            for name, value in metrics.items():
                if value is not None:
                    conn.execute(
                        """INSERT INTO source_metrics
                           (activity_id, source, metric_name, metric_value)
                           VALUES (?, 'garmin', ?, ?)""",
                        (activity_id, name, float(value)),
                    )
        except Exception as e:
            print(f"[garmin] 상세 조회 실패 {source_id}: {e}")

        assign_group_id(conn, activity_id)

    conn.commit()
    return count


def sync_wellness(config: dict, conn: sqlite3.Connection, days: int) -> int:
    """Garmin 웰니스 데이터를 가져와 DB에 저장.

    Args:
        config: 전체 설정 딕셔너리.
        conn: SQLite 연결.
        days: 가져올 일수.

    Returns:
        저장된 레코드 수.
    """
    client = _login(config)
    count = 0
    today = datetime.now().date()

    for i in range(days):
        date = today - timedelta(days=i)
        date_str = date.isoformat()
        sleep_score = None
        sleep_hours = None
        hrv_value = None
        body_battery = None
        stress_avg = None
        resting_hr = None

        try:
            sleep = client.get_sleep_data(date_str)
            if sleep:
                sleep_score = sleep.get("dailySleepDTO", {}).get("sleepScores", {}).get("overall", {}).get("value")
                sleep_secs = sleep.get("dailySleepDTO", {}).get("sleepTimeSeconds")
                if sleep_secs:
                    sleep_hours = round(sleep_secs / 3600, 1)
        except Exception as e:
            print(f"[garmin] 수면 데이터 실패 {date_str}: {e}")

        try:
            time.sleep(2)
            hrv = client.get_hrv_data(date_str)
            if hrv:
                hrv_value = hrv.get("hrvSummary", {}).get("lastNightAvg")
        except Exception as e:
            print(f"[garmin] HRV 데이터 실패 {date_str}: {e}")

        try:
            time.sleep(2)
            bb = client.get_body_battery(date_str)
            if bb and isinstance(bb, list) and len(bb) > 0:
                vals = [item.get("bodyBatteryLevel", 0) for item in bb if item.get("bodyBatteryLevel")]
                body_battery = max(vals) if vals else None
        except Exception as e:
            print(f"[garmin] Body Battery 실패 {date_str}: {e}")

        try:
            time.sleep(2)
            stress = client.get_stress_data(date_str)
            if stress:
                stress_avg = stress.get("averageStressLevel")
        except Exception as e:
            print(f"[garmin] 스트레스 데이터 실패 {date_str}: {e}")

        try:
            resting_hr_data = client.get_rhr_day(date_str)
            if resting_hr_data:
                resting_hr = resting_hr_data.get("restingHeartRate")
        except Exception:
            pass

        has_data = any(v is not None for v in [sleep_score, sleep_hours, hrv_value, body_battery, stress_avg])
        if not has_data:
            continue

        try:
            conn.execute(
                """INSERT OR REPLACE INTO daily_wellness
                   (date, source, sleep_score, sleep_hours, hrv_value,
                    resting_hr, body_battery, stress_avg)
                   VALUES (?, 'garmin', ?, ?, ?, ?, ?, ?)""",
                (date_str, sleep_score, sleep_hours, hrv_value, resting_hr, body_battery, stress_avg),
            )
            count += 1
        except sqlite3.Error as e:
            print(f"[garmin] 웰니스 삽입 실패 {date_str}: {e}")

    conn.commit()
    return count
