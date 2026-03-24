"""Garmin → activity_summaries v2.5 필드 매핑 정의.

이 모듈은 Garmin API 응답 / ZIP export의 필드를 DB 컬럼에 매핑하는
변환 로직을 제공합니다. garmin.py와 backfill에서 공통 사용.
"""

from __future__ import annotations
from datetime import datetime, timezone


def _safe_div(a, b, default=None):
    """0 나누기 방지."""
    if a is None or b is None or b == 0:
        return default
    return a / b


def _epoch_ms_to_iso(epoch_ms) -> str | None:
    """Epoch milliseconds → ISO 8601 문자열."""
    if epoch_ms is None:
        return None
    try:
        dt = datetime.fromtimestamp(float(epoch_ms) / 1000, tz=timezone.utc)
        return dt.strftime("%Y-%m-%dT%H:%M:%S")
    except (ValueError, OSError):
        return None


def extract_summary_fields_from_api(act: dict) -> dict:
    """Garmin API get_activities() 응답 1건 → activity_summaries 컬럼 dict.

    Args:
        act: Garmin Connect API 활동 요약 객체.

    Returns:
        DB 컬럼명 → 값 딕셔너리. None 값은 포함하되 INSERT/UPDATE 시 선택적 사용.
    """
    distance_m = act.get("distance") or 0
    duration_ms = act.get("duration") or 0
    moving_ms = act.get("movingDuration") or 0
    distance_km = distance_m / 1000
    duration_sec = int(duration_ms)
    moving_sec = int(moving_ms)

    avg_pace = round(duration_sec / distance_km) if distance_km > 0 else None

    return {
        "name": act.get("activityName"),
        "activity_type": act.get("activityType", {}).get("typeKey", "running"),
        "sport_type": act.get("activityType", {}).get("typeKey", "running"),
        "start_time": act.get("startTimeLocal", ""),
        "distance_km": distance_km,
        "duration_sec": duration_sec,
        "moving_time_sec": moving_sec,
        "elapsed_time_sec": duration_sec,
        "avg_pace_sec_km": avg_pace,
        "avg_hr": act.get("averageHR"),
        "max_hr": act.get("maxHR"),
        "avg_cadence": act.get("averageRunningCadenceInStepsPerMinute"),
        "max_cadence": act.get("maxRunningCadenceInStepsPerMinute"),
        "elevation_gain": act.get("elevationGain"),
        "elevation_loss": act.get("elevationLoss"),
        "calories": act.get("calories"),
        "bmr_calories": act.get("bmrCalories"),
        "description": act.get("activityName"),
        "avg_speed_ms": act.get("averageSpeed"),
        "max_speed_ms": act.get("maxSpeed"),
        "avg_power": act.get("averagePower"),
        "max_power": act.get("maxPower"),
        "normalized_power": act.get("normPower"),
        "avg_stride_length_cm": act.get("avgStrideLengthCM") or act.get("averageStrideLength"),
        "avg_vertical_oscillation_cm": act.get("avgVerticalOscillationCM") or act.get("avgVerticalOscillation"),
        "avg_vertical_ratio_percent": act.get("avgVerticalRatioPct") or act.get("avgVerticalRatio"),
        "avg_ground_contact_time_ms": act.get("avgGroundContactTimeMilli") or act.get("avgGroundContactTime"),
        "avg_ground_contact_balance": act.get("avgGroundContactBalance"),
        "avg_double_cadence": act.get("avgDoubleCadence"),
        "aerobic_training_effect": act.get("aerobicTrainingEffect"),
        "anaerobic_training_effect": act.get("anaerobicTrainingEffect"),
        "training_load": act.get("activityTrainingLoad"),
        "vo2max_activity": act.get("vO2MaxValue"),
        "steps": act.get("steps"),
        "lap_count": act.get("lapCount"),
        "start_lat": act.get("startLatitude"),
        "start_lon": act.get("startLongitude"),
        "end_lat": act.get("endLatitude"),
        "end_lon": act.get("endLongitude"),
        "min_lat": act.get("minLatitude"),
        "max_lat": act.get("maxLatitude"),
        "min_lon": act.get("minLongitude"),
        "max_lon": act.get("maxLongitude"),
        "min_elevation": act.get("minElevation"),
        "max_elevation": act.get("maxElevation"),
        "max_vertical_speed": act.get("maxVerticalSpeed"),
        "min_temperature": act.get("minTemperature"),
        "max_temperature": act.get("maxTemperature"),
        "avg_temperature": act.get("avgTemperature"),
        "body_battery_diff": act.get("differenceBodyBattery"),
        "water_estimated_ml": act.get("waterEstimated"),
        "moderate_intensity_min": act.get("moderateIntensityMinutes"),
        "vigorous_intensity_min": act.get("vigorousIntensityMinutes"),
        "device_id": str(act.get("deviceId", "")) if act.get("deviceId") else None,
        "favorite": act.get("favorite"),
    }


def extract_summary_fields_from_zip(act: dict) -> dict:
    """Garmin ZIP export summarizedActivities 1건 → activity_summaries 컬럼 dict.

    ZIP export는 API와 키 이름/단위가 다름:
    - distance: cm → km
    - duration/movingDuration: ms → sec
    - avgSpeed: ×10 = m/s
    - elevation: cm → m (elevationGain/Loss는 cm/100)
    - avgStrideLength: cm (그대로, DB도 cm)
    - avgVerticalOscillation: mm → ÷10 = cm? (DB는 cm)
    - hrTimeInZone: ms → sec
    - startTimeLocal: epoch ms
    """
    distance_cm = act.get("distance") or 0
    duration_ms = act.get("duration") or 0
    moving_ms = act.get("movingDuration") or 0

    distance_km = distance_cm / 100_000
    duration_sec = int(duration_ms / 1000)
    moving_sec = int(moving_ms / 1000)

    avg_pace = round(duration_sec / distance_km) if distance_km > 0 else None

    # startTimeLocal은 epoch ms
    start_time_raw = act.get("startTimeLocal")
    start_time = _epoch_ms_to_iso(start_time_raw) if isinstance(start_time_raw, (int, float)) else str(start_time_raw or "")

    # elevation: cm → m
    def _cm_to_m(v):
        return v / 100 if v is not None else None

    # avgSpeed: 특수단위 → ×10 = m/s
    avg_speed_raw = act.get("avgSpeed")
    avg_speed_ms = avg_speed_raw * 10 if avg_speed_raw is not None else None

    max_speed_raw = act.get("maxSpeed")
    max_speed_ms = max_speed_raw * 10 if max_speed_raw is not None else None

    for i in range(7):
        key = f"hrTimeInZone_{i}"

    for i in range(6):
        key = f"powerTimeInZone_{i}"

    result = {
        "name": act.get("name") or act.get("activityName"),
        "activity_type": act.get("activityType", "running"),
        "sport_type": act.get("sportType", "").lower() if act.get("sportType") else None,
        "start_time": start_time,
        "distance_km": distance_km,
        "duration_sec": duration_sec,
        "moving_time_sec": moving_sec,
        "elapsed_time_sec": duration_sec,
        "avg_pace_sec_km": avg_pace,
        "avg_hr": act.get("avgHr"),
        "max_hr": act.get("maxHr"),
        "avg_cadence": act.get("avgRunCadence"),
        "max_cadence": act.get("maxRunCadence"),
        "elevation_gain": _cm_to_m(act.get("elevationGain")),
        "elevation_loss": _cm_to_m(act.get("elevationLoss")),
        "calories": act.get("calories"),
        "bmr_calories": act.get("bmrCalories"),
        "description": act.get("description"),
        "avg_speed_ms": avg_speed_ms,
        "max_speed_ms": max_speed_ms,
        "avg_power": act.get("avgPower"),
        "max_power": act.get("maxPower"),
        "normalized_power": act.get("normPower"),
        "avg_stride_length_cm": act.get("avgStrideLength"),  # cm
        "avg_vertical_oscillation_cm": act.get("avgVerticalOscillation"),  # mm? 확인 필요
        "avg_vertical_ratio_percent": act.get("avgVerticalRatio"),
        "avg_ground_contact_time_ms": act.get("avgGroundContactTime"),  # ms
        "avg_double_cadence": act.get("avgDoubleCadence"),
        "avg_fractional_cadence": act.get("avgFractionalCadence"),
        "max_fractional_cadence": act.get("maxFractionalCadence"),
        "avg_grade_adjusted_speed": act.get("avgGradeAdjustedSpeed"),
        "aerobic_training_effect": act.get("aerobicTrainingEffect"),
        "anaerobic_training_effect": act.get("anaerobicTrainingEffect"),
        "training_load": act.get("activityTrainingLoad"),
        "vo2max_activity": act.get("vO2MaxValue"),
        "workout_label": act.get("trainingEffectLabel"),
        "steps": act.get("steps"),
        "lap_count": act.get("lapCount"),
        "start_lat": act.get("startLatitude"),
        "start_lon": act.get("startLongitude"),
        "end_lat": act.get("endLatitude"),
        "end_lon": act.get("endLongitude"),
        "min_lat": act.get("minLatitude"),
        "max_lat": act.get("maxLatitude"),
        "min_lon": act.get("minLongitude"),
        "max_lon": act.get("maxLongitude"),
        "min_elevation": _cm_to_m(act.get("minElevation")),
        "max_elevation": _cm_to_m(act.get("maxElevation")),
        "max_vertical_speed": act.get("maxVerticalSpeed"),
        "min_temperature": act.get("minTemperature"),
        "max_temperature": act.get("maxTemperature"),
        "body_battery_diff": act.get("differenceBodyBattery"),
        "water_estimated_ml": act.get("waterEstimated"),
        "moderate_intensity_min": act.get("moderateIntensityMinutes"),
        "vigorous_intensity_min": act.get("vigorousIntensityMinutes"),
        "device_id": str(act.get("deviceId", "")) if act.get("deviceId") else None,
        "favorite": act.get("favorite"),
    }

    # HR/Power zone times 추가

    return result


def extract_detail_fields(detail: dict, act: dict | None = None) -> dict:
    """Garmin detail API 응답 → activity_summaries UPDATE용 컬럼 dict.

    detail API에만 있는 추가 필드를 추출합니다.
    act는 원래 활동 요약 (fallback용).
    """
    summary = detail.get("summaryDTO", {})

    def _pick(*keys, sources=None):
        """여러 소스에서 첫 번째 non-None 값 선택."""
        srcs = sources or [detail, summary]
        if act:
            srcs.append(act)
        for src in srcs:
            for k in keys:
                v = src.get(k)
                if v is not None:
                    return v
        return None

    result = {}

    # 기본 필드 (act 목록에 없을 수 있는 것들)
    result["avg_power"] = _pick("averagePower")
    result["normalized_power"] = _pick("normalizedPower", "normPower")
    result["steps"] = _pick("steps")
    result["avg_speed_ms"] = _pick("averageSpeed")
    result["max_speed_ms"] = _pick("maxSpeed")
    result["avg_cadence"] = _pick("averageRunCadence", "averageRunningCadenceInStepsPerMinute")
    result["max_cadence"] = _pick("maxRunCadence", "maxRunningCadenceInStepsPerMinute")
    result["avg_stride_length_cm"] = _pick("averageStrideLength")
    result["avg_vertical_ratio_percent"] = _pick("avgVerticalRatio")
    result["avg_ground_contact_time_ms"] = _pick("avgGroundContactTime")
    result["avg_vertical_oscillation_cm"] = _pick("avgVerticalOscillation")
    result["avg_ground_contact_balance"] = _pick("avgGroundContactBalance")
    result["avg_hr_gap"] = _pick("avgHrGap")
    result["avg_grade_adjusted_speed"] = _pick("avgGradeAdjustedSpeed")
    result["max_double_cadence"] = _pick("maxDoubleCadence")

    # 훈련 효과
    result["aerobic_training_effect"] = _pick("aerobicTrainingEffect")
    result["anaerobic_training_effect"] = _pick("anaerobicTrainingEffect")
    result["training_load"] = _pick("activityTrainingLoad")
    result["vo2max_activity"] = _pick("vO2MaxValue")
    result["workout_label"] = _pick("trainingEffectLabel")



    # None 값 제거 (UPDATE 시 기존 값을 덮어쓰지 않도록)
    return {k: v for k, v in result.items() if v is not None}


def build_upsert_sql(table: str, fields: dict, key_col: str = "id") -> tuple[str, list]:
    """UPDATE SET 구문 생성. None 값은 제외됨.

    Returns:
        (SQL문, 파라미터 리스트)
    """
    non_null = {k: v for k, v in fields.items() if v is not None}
    if not non_null:
        return "", []

    set_clause = ", ".join(f"{col} = ?" for col in non_null.keys())
    sql = f"UPDATE {table} SET {set_clause} WHERE {key_col} = ?"
    params = list(non_null.values())
    return sql, params
