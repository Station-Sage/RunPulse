from __future__ import annotations

"""Garmin 활동 동기화."""

import sqlite3
import time
from datetime import datetime, timedelta

from src.sync.garmin_auth import Garmin, GarminConnectTooManyRequestsError, _login
from src.sync.garmin_helpers import (
    _store_raw_payload,
    _upsert_vo2max,
    _handle_rate_limit,
)
from src.sync.garmin_v2_mappings import extract_summary_fields_from_api, extract_detail_fields
from src.sync.garmin_api_extensions import (
    sync_activity_streams,
    sync_activity_gear,
    sync_activity_exercise_sets,
    sync_activity_weather,
    sync_activity_hr_zones,
    sync_activity_power_zones,
)
from src.utils.dedup import assign_group_id
from src.utils.raw_payload import update_changed_fields
from src.utils.sync_policy import POLICIES
from src.utils.sync_state import mark_finished


def sync_activities(
    config: dict,
    conn: sqlite3.Connection,
    days: int,
    client: "Garmin | None" = None,
    from_date: str | None = None,
    to_date: str | None = None,
    bg_mode: bool = False,
) -> int:
    """Garmin 활동 데이터를 가져와 DB에 저장.

    Args:
        config: 전체 설정 딕셔너리.
        conn: SQLite 연결.
        days: 가져올 일수 (from_date 미지정 시 사용).
        client: 기존 Garmin 클라이언트. None이면 새로 로그인.
        from_date: 기간 동기화 시작일 (YYYY-MM-DD). 지정 시 days 무시.
        to_date: 기간 동기화 종료일 (YYYY-MM-DD). None이면 오늘.
        bg_mode: True이면 mark_running/mark_finished 호출 생략 (bg_sync 관리).

    Returns:
        새로 저장된 활동 수.
    """
    if client is None:
        client = _login(config)

    if from_date:
        cutoff = datetime.fromisoformat(from_date)
        cutoff_end: datetime | None = (
            datetime.fromisoformat(to_date) + timedelta(days=1)
            if to_date else None
        )
        fetch_days = (datetime.now() - cutoff).days + 2
    else:
        cutoff = datetime.now() - timedelta(days=days)
        cutoff_end = None
        fetch_days = days

    activity_summaries = client.get_activities(0, fetch_days * 3)
    count = 0

    for act in activity_summaries:
        start_time = act.get("startTimeLocal", "")
        if not start_time:
            continue

        try:
            act_dt = datetime.fromisoformat(start_time)
            if act_dt < cutoff:
                continue
            if cutoff_end and act_dt >= cutoff_end:
                continue
        except ValueError:
            continue

        source_id = str(act.get("activityId", ""))
        distance_km = (act.get("distance") or 0) / 1000
        duration_sec = int(act.get("duration") or 0)
        avg_pace = round(duration_sec / distance_km) if distance_km > 0 else None

        summary_fields = extract_summary_fields_from_api(act)
        summary_fields["source"] = "garmin"
        summary_fields["source_id"] = source_id
        summary_fields["activity_type"] = act.get("activityType", {}).get("typeKey", "running")
        summary_fields["start_time"] = start_time
        summary_fields["distance_km"] = distance_km
        summary_fields["duration_sec"] = duration_sec
        summary_fields["avg_pace_sec_km"] = avg_pace

        try:
            cols = ", ".join(summary_fields.keys())
            placeholders = ", ".join(["?"] * len(summary_fields))
            cursor = conn.execute(
                f"INSERT OR IGNORE INTO activity_summaries ({cols}) VALUES ({placeholders})",
                list(summary_fields.values())
            )
        except sqlite3.Error as e:
            print(f"[garmin] 활동 삽입 실패 {source_id}: {e}")
            continue

        if cursor.rowcount == 0:
            existing_id = update_changed_fields(conn, "garmin", source_id, summary_fields)
            if existing_id:
                _store_raw_payload(conn, "activity_summary", source_id, act, activity_id=existing_id)
            continue

        activity_id = cursor.lastrowid
        count += 1

        _store_raw_payload(
            conn,
            entity_type="activity_summary",
            entity_id=source_id,
            payload=act,
            activity_id=activity_id,
        )

        try:
            time.sleep(POLICIES["garmin"].per_request_sleep_sec)
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

            te_label = summary.get("trainingEffectLabel") or detail.get("trainingEffectLabel")
            if te_label:
                conn.execute(
                    "UPDATE activity_summaries SET workout_label = ? WHERE id = ?",
                    (te_label, activity_id),
                )

            avg_power = detail.get("averagePower", summary.get("averagePower"))
            normalized_power = (
                detail.get("normalizedPower") or detail.get("normPower")
                or summary.get("normalizedPower") or summary.get("normPower")
            )
            steps = (
                detail.get("steps") or summary.get("steps") or act.get("steps")
            )
            avg_speed = (
                detail.get("averageSpeed") or summary.get("averageSpeed") or act.get("averageSpeed")
            )
            max_speed = (
                detail.get("maxSpeed") or summary.get("maxSpeed") or act.get("maxSpeed")
            )
            avg_run_cadence = (
                detail.get("averageRunCadence") or summary.get("averageRunCadence")
                or act.get("averageRunningCadenceInStepsPerMinute")
            )
            max_run_cadence = (
                detail.get("maxRunCadence") or summary.get("maxRunCadence")
                or act.get("maxRunningCadenceInStepsPerMinute")
            )
            avg_stride_length = (
                detail.get("averageStrideLength") or summary.get("averageStrideLength")
            )
            avg_vertical_ratio = (
                detail.get("avgVerticalRatio") or summary.get("avgVerticalRatio")
            )
            avg_ground_contact_time = (
                detail.get("avgGroundContactTime") or summary.get("avgGroundContactTime")
            )

            hr_zone_times = summary.get("hrTimeInZone", []) or detail.get("hrTimeInZone", [])
            power_zone_times = summary.get("powerTimeInZone", []) or detail.get("powerTimeInZone", [])

            metrics = {
                "training_effect_aerobic": aerobic_te,
                "training_effect_anaerobic": anaerobic_te,
                "training_effect": aerobic_te,
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

            detail_fields = extract_detail_fields(act, detail)
            if detail_fields:
                set_clause = ", ".join(f"{k}=?" for k in detail_fields.keys())
                conn.execute(
                    f"UPDATE activity_summaries SET {set_clause} WHERE id=?",
                    list(detail_fields.values()) + [activity_id]
                )

            for name, value in metrics.items():
                if value is not None:
                    conn.execute(
                        """INSERT INTO activity_detail_metrics
                           (activity_id, source, metric_name, metric_value)
                           VALUES (?, 'garmin', ?, ?)""",
                        (activity_id, name, float(value)),
                    )

            if vo2max is not None:
                date_str = start_time[:10]
                _upsert_vo2max(conn, date_str, float(vo2max))

        except GarminConnectTooManyRequestsError:
            _handle_rate_limit("garmin", source_id)
            conn.commit()
            if not bg_mode:
                mark_finished("garmin", count=count, partial=True,
                              error="Garmin 요청 제한 발생. 잠시 후 다시 시도하세요.")
            return count
        except Exception as e:
            msg = str(e)
            if "1015" in msg or "Too Many Requests" in msg or "429" in msg:
                _handle_rate_limit("garmin", source_id)
                conn.commit()
                if not bg_mode:
                    mark_finished("garmin", count=count, partial=True,
                                  error="Garmin 요청 제한(Error 1015). 약 15분 후 재시도하세요.")
                return count
            print(f"[garmin] 상세 조회 실패 {source_id}: {e}")

        try:
            time.sleep(POLICIES["garmin"].per_request_sleep_sec)
            _sync_activity_splits(conn, client, activity_id, source_id)
        except Exception as e:
            print(f"[garmin] splits 동기화 실패 {source_id}: {e}")

        # 활동 확장 API (streams, gear, exercise_sets)
        try:
            time.sleep(POLICIES["garmin"].per_request_sleep_sec)
            force_refetch = bool(from_date)  # 기간 동기화 = force
            sync_activity_streams(conn, client, activity_id, source_id, force=force_refetch)
        except Exception as e:
            print(f"[garmin] streams 동기화 실패 {source_id}: {e}")

        try:
            time.sleep(POLICIES["garmin"].per_request_sleep_sec)
            sync_activity_gear(conn, client, activity_id, source_id)
        except Exception as e:
            print(f"[garmin] gear 동기화 실패 {source_id}: {e}")

        try:
            time.sleep(POLICIES["garmin"].per_request_sleep_sec)
            sync_activity_exercise_sets(conn, client, activity_id, source_id)
        except Exception as e:
            print(f"[garmin] exercise_sets 동기화 실패 {source_id}: {e}")

        try:
            time.sleep(POLICIES["garmin"].per_request_sleep_sec)
            sync_activity_weather(conn, client, activity_id, source_id)
        except Exception as e:
            print(f"[garmin] activity_weather 동기화 실패 {source_id}: {e}")

        try:
            time.sleep(POLICIES["garmin"].per_request_sleep_sec)
            sync_activity_hr_zones(conn, client, activity_id, source_id)
        except Exception as e:
            print(f"[garmin] hr_zones 동기화 실패 {source_id}: {e}")

        try:
            time.sleep(POLICIES["garmin"].per_request_sleep_sec)
            sync_activity_power_zones(conn, client, activity_id, source_id)
        except Exception as e:
            print(f"[garmin] power_zones 동기화 실패 {source_id}: {e}")

        assign_group_id(conn, activity_id)

    conn.commit()
    if not bg_mode:
        mark_finished("garmin", count=count)
    return count


def _sync_activity_splits(conn: sqlite3.Connection, client, activity_id: int, source_id: str) -> int:
    """Garmin typed_splits → activity_laps 테이블 저장."""
    try:
        data = client.get_activity_typed_splits(int(source_id))
    except Exception as e:
        print(f"[garmin] splits 조회 실패 {source_id}: {e}")
        return 0

    splits = data.get("splits", [])
    if not splits:
        return 0

    count = 0
    for i, s in enumerate(splits):
        fields = {
            "activity_id": activity_id,
            "source": "garmin",
            "lap_index": s.get("messageIndex", i),
            "split_type": s.get("type"),
            "start_time": s.get("startTimeLocal", ""),
            "distance_km": round((s.get("distance") or 0) / 1000, 3),
            "duration_sec": s.get("duration"),
            "moving_time_sec": s.get("movingDuration"),
            "elapsed_time_sec": s.get("elapsedDuration"),
            "avg_pace_sec_km": round(s["duration"] / (s["distance"] / 1000))
                if s.get("distance") and s.get("duration") else None,
            "avg_hr": s.get("averageHR"),
            "max_hr": s.get("maxHR"),
            "avg_cadence": s.get("averageRunCadence"),
            "max_cadence": s.get("maxRunCadence"),
            "elevation_gain": s.get("elevationGain"),
            "total_ascent": s.get("elevationGain"),
            "total_descent": s.get("elevationLoss"),
            "avg_speed_ms": s.get("averageSpeed"),
            "avg_moving_speed_ms": s.get("averageMovingSpeed"),
            "max_speed_ms": s.get("maxSpeed"),
            "total_calories": s.get("calories"),
            "avg_temperature": s.get("averageTemperature"),
            "avg_power": s.get("averagePower"),
            "max_power": s.get("maxPower"),
            "normalized_power": s.get("normalizedPower"),
            "avg_ground_contact_time_ms": s.get("groundContactTime"),
            "avg_stride_length_cm": s.get("strideLength"),
            "avg_vertical_oscillation_cm": s.get("verticalOscillation"),
            "avg_vertical_ratio_pct": s.get("verticalRatio"),
            "start_lat": s.get("startLatitude"),
            "start_lon": s.get("startLongitude"),
            "end_lat": s.get("endLatitude"),
            "end_lon": s.get("endLongitude"),
            "start_elevation": s.get("startElevation"),
            "avg_grade_adjusted_speed_ms": s.get("avgGradeAdjustedSpeed"),
        }

        fields = {k: v for k, v in fields.items() if v is not None}
        cols = ", ".join(fields.keys())
        placeholders = ", ".join(["?"] * len(fields))
        try:
            conn.execute(
                f"INSERT OR REPLACE INTO activity_laps ({cols}) VALUES ({placeholders})",
                list(fields.values())
            )
            count += 1
        except Exception as e:
            print(f"[garmin] lap 삽입 실패 {source_id} idx {i}: {e}")

    return count
