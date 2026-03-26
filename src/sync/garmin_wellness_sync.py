from __future__ import annotations

"""Garmin 웰니스 데이터 동기화."""

import sqlite3
import time
from datetime import datetime, timedelta

from src.sync.garmin_auth import Garmin, _login
from src.sync.garmin_helpers import (
    _store_raw_payload,
    _upsert_vo2max,
    _store_daily_detail_metrics,
)


def sync_wellness(
    config: dict,
    conn: sqlite3.Connection,
    days: int,
    client: "Garmin | None" = None,
    from_date: str | None = None,
    to_date: str | None = None,
) -> int:
    """Garmin 웰니스 데이터를 가져와 DB에 저장.

    Args:
        config: 전체 설정 딕셔너리.
        conn: SQLite 연결.
        days: 가져올 일수 (from_date 미지정 시).
        client: 기존 Garmin 클라이언트. None이면 새로 로그인.
        from_date: 기간 동기화 시작일 (YYYY-MM-DD). 지정 시 days 무시.
        to_date: 기간 동기화 종료일.

    Returns:
        저장된 레코드 수.
    """
    if client is None:
        client = _login(config)

    count = 0
    today = datetime.now().date()

    # from_date 지정 시 해당 기간 전체
    if from_date:
        from datetime import date as _date
        start = _date.fromisoformat(from_date)
        end = _date.fromisoformat(to_date) if to_date else today
        days = (end - start).days + 1
        today = end

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
                    daily_sleep.get("averageHeartRate") or sleep.get("averageHeartRate")
                )
                readiness_score = (
                    sleep.get("readinessScore") or daily_sleep.get("readinessScore")
                    or sleep.get("readiness") or daily_sleep.get("readiness")
                )
                weight_kg = (
                    sleep.get("weight") or sleep.get("weightKg")
                    or daily_sleep.get("weight") or daily_sleep.get("weightKg")
                    or daily_sleep.get("bodyWeight")
                )
                steps = (
                    sleep.get("steps") or daily_sleep.get("steps")
                    or sleep.get("totalSteps") or daily_sleep.get("totalSteps")
                )
                resting_hr = (
                    daily_sleep.get("restingHeartRate") or sleep.get("restingHeartRate")
                )
                detail_metrics.update({
                    "sleep_stage_awake_sec": (
                        daily_sleep.get("awakeSleepSeconds") or daily_sleep.get("awakeSeconds")
                    ),
                    "sleep_stage_light_sec": (
                        daily_sleep.get("lightSleepSeconds") or daily_sleep.get("lightSeconds")
                    ),
                    "sleep_stage_deep_sec": (
                        daily_sleep.get("deepSleepSeconds") or daily_sleep.get("deepSeconds")
                    ),
                    "sleep_stage_rem_sec": (
                        daily_sleep.get("remSleepSeconds") or daily_sleep.get("remSeconds")
                    ),
                    "sleep_total_sec": (
                        daily_sleep.get("sleepTimeSeconds") or daily_sleep.get("totalSleepSeconds")
                    ),
                    "sleep_restless_moments": (
                        daily_sleep.get("restlessMomentsCount") or daily_sleep.get("restlessMoments")
                    ),
                    "sleep_avg_respiration": (
                        daily_sleep.get("averageRespiration") or daily_sleep.get("avgRespiration")
                    ),
                    "sleep_avg_spo2": (
                        daily_sleep.get("averageSpO2") or daily_sleep.get("avgSpO2")
                    ),
                })
                sleep_start = (
                    daily_sleep.get("sleepStartTimestampLocal")
                    or daily_sleep.get("sleepStartTimestampGMT")
                )
                sleep_end = (
                    daily_sleep.get("sleepEndTimestampLocal")
                    or daily_sleep.get("sleepEndTimestampGMT")
                )
                if sleep_start is not None:
                    detail_json_metrics["sleep_start_timestamp"] = {"value": sleep_start}
                if sleep_end is not None:
                    detail_json_metrics["sleep_end_timestamp"] = {"value": sleep_end}
                detail_json_metrics["sleep_summary_json"] = {
                    "dailySleepDTO": daily_sleep,
                    "top_level": {k: v for k, v in sleep.items() if k != "dailySleepDTO"},
                }
        except Exception as e:
            print(f"[garmin] 수면 데이터 실패 {date_str}: {e}")

        try:
            time.sleep(2)
            hrv = client.get_hrv_data(date_str)
            _store_raw_payload(conn, "hrv_day", date_str, hrv)
            if hrv:
                hrv_summary = hrv.get("hrvSummary", {})
                hrv_value = (
                    hrv_summary.get("lastNightAvg") or hrv.get("lastNightAvg")
                )
                hrv_sdnn = (
                    hrv_summary.get("sdnn") or hrv_summary.get("lastNightSDNN")
                    or hrv.get("sdnn") or hrv.get("lastNightSDNN")
                )
                detail_metrics.update({
                    "overnight_hrv_avg": hrv_value,
                    "overnight_hrv_sdnn": hrv_sdnn,
                    "hrv_weekly_avg": (
                        hrv_summary.get("weeklyAvg") or hrv.get("weeklyAvg")
                    ),
                    "hrv_baseline_low": (
                        hrv_summary.get("baselineLow") or hrv.get("baselineLow")
                    ),
                    "hrv_baseline_high": (
                        hrv_summary.get("baselineHigh") or hrv.get("baselineHigh")
                    ),
                })
                hrv_status = hrv_summary.get("status") or hrv.get("status")
                if hrv_status is not None:
                    detail_json_metrics["hrv_status"] = {"value": hrv_status}
                detail_json_metrics["hrv_summary_json"] = {
                    "hrvSummary": hrv_summary,
                    "top_level": {k: v for k, v in hrv.items() if k != "hrvSummary"},
                }
        except Exception as e:
            print(f"[garmin] HRV 데이터 실패 {date_str}: {e}")

        try:
            time.sleep(2)
            bb = client.get_body_battery(date_str)
            _store_raw_payload(conn, "body_battery_day", date_str, bb)
            if bb and isinstance(bb, list) and bb:
                item = bb[0]
                bb_vals_array = item.get("bodyBatteryValuesArray") or []
                vals = [pair[1] for pair in bb_vals_array
                        if len(pair) > 1 and pair[1] is not None]
                charged = item.get("charged")
                drained = item.get("drained")
                body_battery = max(vals) if vals else None
                if vals:
                    detail_metrics.update({
                        "body_battery_start": vals[0],
                        "body_battery_end": vals[-1],
                        "body_battery_min": min(vals),
                        "body_battery_max": max(vals),
                        "body_battery_samples": len(vals),
                        "body_battery_delta": vals[-1] - vals[0],
                    })
                if charged is not None:
                    detail_metrics["body_battery_charged"] = charged
                if drained is not None:
                    detail_metrics["body_battery_drained"] = drained
                detail_json_metrics["body_battery_timeline"] = bb_vals_array
                detail_json_metrics["body_battery_summary_json"] = {
                    "sample_count": len(vals),
                    "min": min(vals) if vals else None,
                    "max": max(vals) if vals else None,
                    "start": vals[0] if vals else None,
                    "end": vals[-1] if vals else None,
                    "charged": charged,
                    "drained": drained,
                }
        except Exception as e:
            print(f"[garmin] Body Battery 실패 {date_str}: {e}")

        try:
            time.sleep(2)
            stress = client.get_stress_data(date_str)
            _store_raw_payload(conn, "stress_day", date_str, stress)
            if stress:
                stress_avg = stress.get("averageStressLevel") or stress.get("avgStressLevel")
                stress_values = stress.get("stressValuesArray") or stress.get("stressTimeline")

                def _stress_durations(vals: list) -> dict:
                    if not vals or len(vals) < 2:
                        return {}
                    interval_sec = (vals[1][0] - vals[0][0]) / 1000
                    rest = low = medium = high = 0
                    for _, lvl in vals:
                        if lvl is None or lvl < 0:
                            continue
                        if lvl <= 25:
                            rest += interval_sec
                        elif lvl <= 50:
                            low += interval_sec
                        elif lvl <= 75:
                            medium += interval_sec
                        else:
                            high += interval_sec
                    return {
                        "stress_rest_duration": int(rest) if rest else None,
                        "stress_low_duration": int(low) if low else None,
                        "stress_medium_duration": int(medium) if medium else None,
                        "stress_high_duration": int(high) if high else None,
                    }

                computed = _stress_durations(stress_values or [])
                detail_metrics.update({
                    "stress_avg": stress_avg,
                    "stress_max": (
                        stress.get("maxStressLevel") or stress.get("dailyStressMax")
                    ),
                    "stress_rest_duration": (
                        stress.get("restStressDuration") or computed.get("stress_rest_duration")
                    ),
                    "stress_low_duration": (
                        stress.get("lowStressDuration") or computed.get("stress_low_duration")
                    ),
                    "stress_medium_duration": (
                        stress.get("mediumStressDuration") or computed.get("stress_medium_duration")
                    ),
                    "stress_high_duration": (
                        stress.get("highStressDuration") or computed.get("stress_high_duration")
                    ),
                })
                if stress_values is not None:
                    detail_json_metrics["stress_timeline"] = stress_values
                detail_json_metrics["stress_summary_json"] = {
                    k: v for k, v in stress.items()
                    if k not in {"stressValuesArray", "stressTimeline"}
                }
        except Exception as e:
            print(f"[garmin] 스트레스 데이터 실패 {date_str}: {e}")

        try:
            time.sleep(2)
            respiration = client.get_respiration_data(date_str)
            _store_raw_payload(conn, "respiration_day", date_str, respiration)
            if respiration:
                detail_metrics.update({
                    "respiration_avg": (
                        respiration.get("averageRespiration")
                        or respiration.get("avgBreathsPerMinute")
                    ),
                    "respiration_min": (
                        respiration.get("minRespiration")
                        or respiration.get("minBreathsPerMinute")
                    ),
                    "respiration_max": (
                        respiration.get("maxRespiration")
                        or respiration.get("maxBreathsPerMinute")
                    ),
                })
                detail_json_metrics["respiration_summary_json"] = respiration
        except Exception:
            pass

        try:
            time.sleep(2)
            spo2 = client.get_spo2_data(date_str)
            _store_raw_payload(conn, "spo2_day", date_str, spo2)
            if spo2:
                detail_metrics.update({
                    "spo2_avg": (
                        spo2.get("averageSpO2") or spo2.get("avgSpO2") or spo2.get("averageValue")
                    ),
                    "spo2_min": (
                        spo2.get("minSpO2") or spo2.get("minimumSpO2") or spo2.get("minValue")
                    ),
                    "spo2_max": (
                        spo2.get("maxSpO2") or spo2.get("maximumSpO2") or spo2.get("maxValue")
                    ),
                })
                detail_json_metrics["spo2_summary_json"] = spo2
        except Exception:
            pass

        try:
            time.sleep(2)
            readiness = client.get_training_readiness(date_str)
            _store_raw_payload(conn, "training_readiness_day", date_str, readiness)
            if readiness:
                detail_metrics.update({
                    "training_readiness_score": (
                        readiness.get("score") or readiness.get("readinessScore")
                        or readiness.get("trainingReadinessScore")
                    ),
                    "training_readiness_sleep_score": (
                        readiness.get("sleepScore") or readiness.get("sleepContribution")
                    ),
                    "training_readiness_recovery_score": (
                        readiness.get("recoveryScore") or readiness.get("recoveryContribution")
                    ),
                    "training_readiness_hrv_score": (
                        readiness.get("hrvScore") or readiness.get("hrvContribution")
                    ),
                })
                detail_json_metrics["training_readiness_summary_json"] = readiness
        except Exception:
            try:
                time.sleep(2)
                readiness = client.get_morning_training_readiness(date_str)
                _store_raw_payload(conn, "morning_training_readiness_day", date_str, readiness)
                if readiness:
                    detail_metrics.update({
                        "training_readiness_score": (
                            readiness.get("score") or readiness.get("readinessScore")
                        ),
                        "training_readiness_sleep_score": readiness.get("sleepScore"),
                        "training_readiness_recovery_score": readiness.get("recoveryScore"),
                        "training_readiness_hrv_score": readiness.get("hrvScore"),
                    })
            except Exception:
                pass

        try:
            time.sleep(2)
            body_comp = client.get_body_composition(date_str)
            _store_raw_payload(conn, "body_composition_day", date_str, body_comp)
            if body_comp:
                detail_metrics.update({
                    "body_weight_kg": (
                        body_comp.get("weight") or body_comp.get("weightKg")
                    ),
                    "body_fat_pct": (
                        body_comp.get("bodyFat") or body_comp.get("bodyFatPercentage")
                    ),
                    "body_water_pct": (
                        body_comp.get("bodyWater") or body_comp.get("bodyWaterPercentage")
                    ),
                    "skeletal_muscle_mass_kg": (
                        body_comp.get("skeletalMuscleMass") or body_comp.get("muscleMass")
                    ),
                    "bone_mass_kg": body_comp.get("boneMass"),
                    "bmi": body_comp.get("bmi"),
                })
                detail_json_metrics["body_composition_summary_json"] = body_comp
        except Exception:
            pass

        try:
            rhr_data = client.get_rhr_day(date_str)
            _store_raw_payload(conn, "rhr_day", date_str, rhr_data)
            if rhr_data and resting_hr is None:
                resting_hr = rhr_data.get("restingHeartRate")
        except Exception:
            pass

        try:
            time.sleep(2)
            max_metrics = client.get_max_metrics(date_str)
            if max_metrics:
                _store_raw_payload(conn, "max_metrics_day", date_str, max_metrics)
                vo2_val = None
                if isinstance(max_metrics, list):
                    for item in max_metrics:
                        vo2_val = (
                            item.get("generic", {}).get("vo2MaxPreciseValue")
                            or item.get("generic", {}).get("vo2MaxValue")
                            or item.get("vo2MaxPreciseValue")
                            or item.get("vo2MaxValue")
                            or item.get("vo2Max")
                            or vo2_val
                        )
                elif isinstance(max_metrics, dict):
                    vo2_val = (
                        max_metrics.get("generic", {}).get("vo2MaxPreciseValue")
                        or max_metrics.get("generic", {}).get("vo2MaxValue")
                        or max_metrics.get("vo2MaxPreciseValue")
                        or max_metrics.get("vo2MaxValue")
                        or max_metrics.get("vo2Max")
                    )
                if vo2_val is not None:
                    _upsert_vo2max(conn, date_str, float(vo2_val))
                    detail_metrics["garmin_vo2max"] = float(vo2_val)
        except Exception as e:
            print(f"[garmin] VO2max 조회 실패 {date_str}: {e}")

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
