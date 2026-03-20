from __future__ import annotations

"""Garmin Connect 데이터 동기화."""

import json
import sqlite3
import time
from datetime import datetime, timedelta

try:
    from garminconnect import Garmin
except ImportError:  # optional dependency for tests/Termux
    Garmin = None

from src.utils.dedup import assign_group_id


def _login(config: dict) -> Garmin:
    """Garmin Connect 로그인."""
    garmin_cfg = config["garmin"]
    if Garmin is None:
        raise ImportError("garminconnect 패키지가 필요합니다. pip install garminconnect")
    client = Garmin(garmin_cfg["email"], garmin_cfg["password"])
    client.login()
    return client



def _store_raw_payload(
    conn: sqlite3.Connection,
    entity_type: str,
    entity_id: str,
    payload,
    activity_id: int | None = None,
) -> None:
    """Store or update raw Garmin payload."""
    if payload is None:
        return

    payload_json = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    conn.execute(
        """
        INSERT INTO raw_source_payloads
            (source, entity_type, entity_id, activity_id, payload_json)
        VALUES
            ('garmin', ?, ?, ?, ?)
        ON CONFLICT(source, entity_type, entity_id) DO UPDATE SET
            activity_id = excluded.activity_id,
            payload_json = excluded.payload_json,
            updated_at = datetime('now')
        """,
        (entity_type, entity_id, activity_id, payload_json),
    )


def _upsert_vo2max(conn: sqlite3.Connection, date_str: str, vo2max: float) -> None:
    """garmin_vo2max를 daily_fitness에 저장/업데이트."""
    try:
        conn.execute("""
            INSERT INTO daily_fitness (date, source, garmin_vo2max)
            VALUES (?, 'garmin', ?)
            ON CONFLICT(date, source) DO UPDATE SET
                garmin_vo2max = excluded.garmin_vo2max,
                updated_at = datetime('now')
        """, (date_str, vo2max))
    except sqlite3.OperationalError:
        pass  # daily_fitness 테이블 미생성 환경 (graceful)


def _upsert_daily_detail_metric(
    conn: sqlite3.Connection,
    date_str: str,
    metric_name: str,
    metric_value=None,
    metric_json=None,
) -> None:
    """Upsert a Garmin daily detail metric."""
    try:
        conn.execute(
            """
            INSERT INTO daily_detail_metrics
                (date, source, metric_name, metric_value, metric_json)
            VALUES
                (?, 'garmin', ?, ?, ?)
            ON CONFLICT(date, source, metric_name) DO UPDATE SET
                metric_value = excluded.metric_value,
                metric_json = excluded.metric_json,
                updated_at = datetime('now')
            """,
            (date_str, metric_name, metric_value, metric_json),
        )
    except sqlite3.OperationalError:
        pass


def _store_daily_detail_metrics(
    conn: sqlite3.Connection,
    date_str: str,
    numeric_metrics: dict[str, float | int | None],
    json_metrics: dict[str, object] | None = None,
) -> None:
    """Store multiple Garmin daily detail metrics."""
    for metric_name, metric_value in numeric_metrics.items():
        if metric_value is not None:
            _upsert_daily_detail_metric(conn, date_str, metric_name, metric_value=metric_value)

    if json_metrics:
        for metric_name, payload in json_metrics.items():
            if payload is not None:
                _upsert_daily_detail_metric(
                    conn,
                    date_str,
                    metric_name,
                    metric_json=json.dumps(payload, ensure_ascii=False, sort_keys=True),
                )


def sync_activities(
    config: dict,
    conn: sqlite3.Connection,
    days: int,
    client: Garmin | None = None,
) -> int:
    """Garmin 활동 데이터를 가져와 DB에 저장.

    Args:
        config: 전체 설정 딕셔너리.
        conn: SQLite 연결.
        days: 가져올 일수.
        client: 기존 Garmin 클라이언트. None이면 새로 로그인.

    Returns:
        새로 저장된 활동 수.
    """
    if client is None:
        client = _login(config)

    activity_summaries = client.get_activities(0, days * 3)
    cutoff = datetime.now() - timedelta(days=days)
    count = 0

    for act in activity_summaries:
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
                """INSERT OR IGNORE INTO activity_summaries
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

        _store_raw_payload(
            conn,
            entity_type="activity_summary",
            entity_id=source_id,
            payload=act,
            activity_id=activity_id,
        )

        # 상세 지표 조회
        try:
            time.sleep(2)
            detail = client.get_activity(int(source_id))
            _store_raw_payload(
                conn,
                entity_type="activity_detail",
                entity_id=source_id,
                payload=detail,
                activity_id=activity_id,
            )
            summary = detail.get("summaryDTO", {})
            aerobic_te = detail.get("aerobicTrainingEffect", summary.get("aerobicTrainingEffect"))
            anaerobic_te = detail.get("anaerobicTrainingEffect", summary.get("anaerobicTrainingEffect"))
            training_load = detail.get("activityTrainingLoad", summary.get("activityTrainingLoad"))
            vo2max = detail.get("vO2MaxValue", summary.get("vO2MaxValue"))

            # aerobic/anaerobic TE 분리 저장 + 하위호환 alias
            avg_power = detail.get("averagePower", summary.get("averagePower"))
            normalized_power = (
                detail.get("normalizedPower")
                or detail.get("normPower")
                or summary.get("normalizedPower")
                or summary.get("normPower")
            )
            steps = (
                detail.get("steps")
                or summary.get("steps")
                or act.get("steps")
            )

            avg_speed = (
                detail.get("averageSpeed")
                or summary.get("averageSpeed")
                or act.get("averageSpeed")
            )
            max_speed = (
                detail.get("maxSpeed")
                or summary.get("maxSpeed")
                or act.get("maxSpeed")
            )
            avg_run_cadence = (
                detail.get("averageRunCadence")
                or summary.get("averageRunCadence")
                or act.get("averageRunningCadenceInStepsPerMinute")
            )
            max_run_cadence = (
                detail.get("maxRunCadence")
                or summary.get("maxRunCadence")
                or act.get("maxRunningCadenceInStepsPerMinute")
            )
            avg_stride_length = (
                detail.get("averageStrideLength")
                or summary.get("averageStrideLength")
            )
            avg_vertical_ratio = (
                detail.get("avgVerticalRatio")
                or summary.get("avgVerticalRatio")
            )
            avg_ground_contact_time = (
                detail.get("avgGroundContactTime")
                or summary.get("avgGroundContactTime")
            )

            hr_zone_times = summary.get("hrTimeInZone", []) or detail.get("hrTimeInZone", [])
            power_zone_times = summary.get("powerTimeInZone", []) or detail.get("powerTimeInZone", [])

            metrics = {
                "training_effect_aerobic": aerobic_te,
                "training_effect_anaerobic": anaerobic_te,
                "training_effect": aerobic_te,  # 하위호환
                "training_load": training_load,
                "vo2max": vo2max,
                "avg_power": avg_power,
                "normalized_power": normalized_power,
                "steps": steps,
                "avg_speed": avg_speed,
                "max_speed": max_speed,
                "avg_run_cadence": avg_run_cadence,
                "max_run_cadence": max_run_cadence,
                "avg_stride_length": avg_stride_length,
                "avg_vertical_ratio": avg_vertical_ratio,
                "avg_ground_contact_time": avg_ground_contact_time,
            }
            for idx, value in enumerate(hr_zone_times[:5], start=1):
                if value is not None:
                    metrics[f"hr_zone_time_{idx}"] = value

            for idx, value in enumerate(power_zone_times[:5], start=1):
                if value is not None:
                    metrics[f"power_zone_time_{idx}"] = value

            for name, value in metrics.items():
                if value is not None:
                    conn.execute(
                        """INSERT INTO activity_detail_metrics
                           (activity_id, source, metric_name, metric_value)
                           VALUES (?, 'garmin', ?, ?)""",
                        (activity_id, name, float(value)),
                    )

            # vo2max를 daily_fitness에도 저장
            if vo2max is not None:
                date_str = start_time[:10]  # YYYY-MM-DD
                _upsert_vo2max(conn, date_str, float(vo2max))

        except Exception as e:
            print(f"[garmin] 상세 조회 실패 {source_id}: {e}")

        assign_group_id(conn, activity_id)

    conn.commit()
    return count


def sync_wellness(
    config: dict,
    conn: sqlite3.Connection,
    days: int,
    client: Garmin | None = None,
) -> int:
    """Garmin 웰니스 데이터를 가져와 DB에 저장.

    Args:
        config: 전체 설정 딕셔너리.
        conn: SQLite 연결.
        days: 가져올 일수.
        client: 기존 Garmin 클라이언트. None이면 새로 로그인.

    Returns:
        저장된 레코드 수.
    """
    if client is None:
        client = _login(config)

    count = 0
    today = datetime.now().date()

    for i in range(days):
        day = today - timedelta(days=i)
        date_str = day.isoformat()
        sleep_score = sleep_hours = hrv_value = hrv_sdnn = body_battery = stress_avg = resting_hr = None
        avg_sleeping_hr = readiness_score = weight_kg = steps = None
        detail_metrics: dict[str, float | int | None] = {}
        detail_json_metrics: dict[str, object] = {}

        try:
            sleep = client.get_sleep_data(date_str)
            _store_raw_payload(conn, "sleep_day", date_str, sleep)
            if sleep:
                daily_sleep = sleep.get("dailySleepDTO", {})
                sleep_score = (daily_sleep.get("sleepScores", {})
                               .get("overall", {}).get("value"))
                sleep_secs = daily_sleep.get("sleepTimeSeconds")
                if sleep_secs:
                    sleep_hours = round(sleep_secs / 3600, 1)

                avg_sleeping_hr = (
                    daily_sleep.get("averageHeartRate")
                    or sleep.get("averageHeartRate")
                )

                readiness_score = (
                    sleep.get("readinessScore")
                    or daily_sleep.get("readinessScore")
                    or sleep.get("readiness")
                    or daily_sleep.get("readiness")
                )

                weight_kg = (
                    sleep.get("weight")
                    or sleep.get("weightKg")
                    or daily_sleep.get("weight")
                    or daily_sleep.get("weightKg")
                    or daily_sleep.get("bodyWeight")
                )

                steps = (
                    sleep.get("steps")
                    or daily_sleep.get("steps")
                    or sleep.get("totalSteps")
                    or daily_sleep.get("totalSteps")
                    or steps
                )

                resting_hr = (
                    daily_sleep.get("restingHeartRate")
                    or sleep.get("restingHeartRate")
                    or resting_hr
                )

                detail_metrics.update({
                    "sleep_stage_awake_sec": (
                        daily_sleep.get("awakeSleepSeconds")
                        or daily_sleep.get("awakeSeconds")
                    ),
                    "sleep_stage_light_sec": (
                        daily_sleep.get("lightSleepSeconds")
                        or daily_sleep.get("lightSeconds")
                    ),
                    "sleep_stage_deep_sec": (
                        daily_sleep.get("deepSleepSeconds")
                        or daily_sleep.get("deepSeconds")
                    ),
                    "sleep_stage_rem_sec": (
                        daily_sleep.get("remSleepSeconds")
                        or daily_sleep.get("remSeconds")
                    ),
                })

                sleep_start = (
                    daily_sleep.get("sleepStartTimestampLocal")
                    or daily_sleep.get("sleepStartTimestampGMT")
                    or daily_sleep.get("sleepStartTimestamp")
                )
                sleep_end = (
                    daily_sleep.get("sleepEndTimestampLocal")
                    or daily_sleep.get("sleepEndTimestampGMT")
                    or daily_sleep.get("sleepEndTimestamp")
                )
                if sleep_start is not None:
                    detail_json_metrics["sleep_start_timestamp"] = {"value": sleep_start}
                if sleep_end is not None:
                    detail_json_metrics["sleep_end_timestamp"] = {"value": sleep_end}
        except Exception as e:
            print(f"[garmin] 수면 데이터 실패 {date_str}: {e}")

        try:
            time.sleep(2)
            hrv = client.get_hrv_data(date_str)
            _store_raw_payload(conn, "hrv_day", date_str, hrv)
            if hrv:
                hrv_summary = hrv.get("hrvSummary", {})
                hrv_value = (
                    hrv_summary.get("lastNightAvg")
                    or hrv.get("lastNightAvg")
                )
                hrv_sdnn = (
                    hrv_summary.get("sdnn")
                    or hrv_summary.get("lastNightSDNN")
                    or hrv.get("sdnn")
                    or hrv.get("lastNightSDNN")
                )

                detail_metrics.update({
                    "overnight_hrv_avg": hrv_value,
                    "overnight_hrv_sdnn": hrv_sdnn,
                    "hrv_weekly_avg": (
                        hrv_summary.get("weeklyAvg")
                        or hrv.get("weeklyAvg")
                    ),
                })

                hrv_status = (
                    hrv_summary.get("status")
                    or hrv.get("status")
                )
                if hrv_status is not None:
                    detail_json_metrics["hrv_status"] = {"value": hrv_status}
        except Exception as e:
            print(f"[garmin] HRV 데이터 실패 {date_str}: {e}")

        try:
            time.sleep(2)
            bb = client.get_body_battery(date_str)
            _store_raw_payload(conn, "body_battery_day", date_str, bb)
            if bb and isinstance(bb, list) and bb:
                vals = [item.get("bodyBatteryLevel", 0) for item in bb
                        if item.get("bodyBatteryLevel") is not None]
                body_battery = max(vals) if vals else None

                if vals:
                    detail_metrics.update({
                        "body_battery_start": vals[0],
                        "body_battery_end": vals[-1],
                        "body_battery_min": min(vals),
                        "body_battery_max": max(vals),
                    })
                    detail_json_metrics["body_battery_timeline"] = bb
        except Exception as e:
            print(f"[garmin] Body Battery 실패 {date_str}: {e}")

        try:
            time.sleep(2)
            stress = client.get_stress_data(date_str)
            _store_raw_payload(conn, "stress_day", date_str, stress)
            if stress:
                stress_avg = stress.get("averageStressLevel")
                if stress_avg is None:
                    stress_avg = stress.get("avgStressLevel")

                detail_metrics.update({
                    "stress_max": (
                        stress.get("maxStressLevel")
                        or stress.get("dailyStressMax")
                    ),
                    "stress_rest_duration": (
                        stress.get("restStressDuration")
                        or stress.get("restDuration")
                    ),
                    "stress_low_duration": (
                        stress.get("lowStressDuration")
                        or stress.get("lowDuration")
                    ),
                    "stress_medium_duration": (
                        stress.get("mediumStressDuration")
                        or stress.get("mediumDuration")
                    ),
                    "stress_high_duration": (
                        stress.get("highStressDuration")
                        or stress.get("highDuration")
                    ),
                })

                stress_values = stress.get("stressValuesArray") or stress.get("stressTimeline")
                if stress_values is not None:
                    detail_json_metrics["stress_timeline"] = stress_values
        except Exception as e:
            print(f"[garmin] 스트레스 데이터 실패 {date_str}: {e}")

        try:
            rhr_data = client.get_rhr_day(date_str)
            _store_raw_payload(conn, "rhr_day", date_str, rhr_data)
            if rhr_data and resting_hr is None:
                resting_hr = rhr_data.get("restingHeartRate")
        except Exception:
            pass

        has_data = any(v is not None for v in
                       [sleep_score, sleep_hours, hrv_value, body_battery, stress_avg])
        if not has_data:
            continue

        try:
            conn.execute(
                """INSERT OR REPLACE INTO daily_wellness
                   (date, source, sleep_score, sleep_hours, hrv_value, hrv_sdnn,
                    resting_hr, avg_sleeping_hr, body_battery, stress_avg,
                    readiness_score, steps, weight_kg)
                   VALUES (?, 'garmin', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (date_str, sleep_score, sleep_hours, hrv_value, hrv_sdnn,
                 resting_hr, avg_sleeping_hr, body_battery, stress_avg,
                 readiness_score, steps, weight_kg),
            )
            _store_daily_detail_metrics(conn, date_str, detail_metrics, detail_json_metrics)
            count += 1
        except sqlite3.Error as e:
            print(f"[garmin] 웰니스 삽입 실패 {date_str}: {e}")

    conn.commit()
    return count


def sync_garmin(config: dict, conn: sqlite3.Connection, days: int) -> dict:
    """Garmin 전체 동기화 (활동 + 웰니스). 클라이언트를 한 번만 로그인.

    Args:
        config: 전체 설정 딕셔너리.
        conn: SQLite 연결.
        days: 가져올 일수.

    Returns:
        {"activity_summaries": 저장 수, "wellness": 저장 수}
    """
    client = _login(config)
    act_count = sync_activities(config, conn, days, client=client)
    well_count = sync_wellness(config, conn, days, client=client)
    return {"activity_summaries": act_count, "wellness": well_count}
