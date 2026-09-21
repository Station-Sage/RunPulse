"""Garmin raw JSON → Layer 1 + Layer 2 변환.

Garmin API 응답 구조:
  - summary: GET /activitylist-service/activities/search/activities 의 한 항목
  - detail: GET /activity-service/activity/{id}/details
  - wellness: 여러 엔드포인트 (sleep, hrv, body_battery, stress, user_summary, etc.)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from src.sync.extractors.base import BaseExtractor, MetricRecord
from src.utils.activity_types import normalize_activity_type


class GarminExtractor(BaseExtractor):

    SOURCE = "garmin"

    # ── Activity Core ──

    def extract_activity_core(self, raw: dict) -> dict:
        """Garmin activity summary JSON → activity_summaries dict (38 cols)."""
        activity_type_obj = raw.get("activityType", {})
        type_key = (
            activity_type_obj.get("typeKey", "unknown")
            if isinstance(activity_type_obj, dict)
            else str(activity_type_obj)
        )

        avg_speed = raw.get("averageSpeed")
        avg_pace = round(1000.0 / avg_speed, 2) if avg_speed and avg_speed > 0 else None

        core = {
            "source": self.SOURCE,
            "source_id": str(raw.get("activityId", "")),
            "name": raw.get("activityName"),
            "activity_type": normalize_activity_type(type_key, self.SOURCE),
            "start_time": raw.get("startTimeLocal") or raw.get("startTimeGMT"),
            # 거리/시간
            "distance_m": raw.get("distance"),
            "duration_sec": _seconds(raw.get("duration")),
            "moving_time_sec": _seconds(raw.get("movingDuration")),
            "elapsed_time_sec": _seconds(raw.get("elapsedDuration")),
            # 속도/페이스
            "avg_speed_ms": avg_speed,
            "max_speed_ms": raw.get("maxSpeed"),
            "avg_pace_sec_km": avg_pace,
            # 심박
            "avg_hr": _int(raw.get("averageHR")),
            "max_hr": _int(raw.get("maxHR")),
            # 케이던스
            "avg_cadence": _running_cadence(raw.get("averageRunningCadenceInStepsPerMinute")),
            "max_cadence": _running_cadence(raw.get("maxRunningCadenceInStepsPerMinute")),
            # 파워
            "avg_power": raw.get("avgPower") or raw.get("averagePower"),
            "max_power": raw.get("maxPower"),
            # 고도
            "elevation_gain": raw.get("elevationGain"),
            "elevation_loss": raw.get("elevationLoss"),
            # 러닝 다이내믹스
            "avg_ground_contact_time_ms": raw.get("avgGroundContactTime")
                or raw.get("avgGroundContactTimeMilli"),
            "avg_stride_length_cm": _stride_to_cm(
                raw.get("avgStrideLength") or raw.get("avgStrideLengthCM")
            ),
            "avg_vertical_oscillation_cm": raw.get("avgVerticalOscillation")
                or raw.get("avgVerticalOscillationCM"),
            "avg_vertical_ratio_pct": raw.get("avgVerticalRatio")
                or raw.get("avgVerticalRatioPct"),
            # 위치
            "start_lat": raw.get("startLatitude"),
            "start_lon": raw.get("startLongitude"),
            "end_lat": raw.get("endLatitude"),
            "end_lon": raw.get("endLongitude"),
            # 환경
            "avg_temperature": _celsius_if_available(raw),
            # 메타
            "description": raw.get("description"),
            "event_type": (
                raw.get("eventType", {}).get("typeKey")
                if isinstance(raw.get("eventType"), dict)
                else raw.get("eventType")
            ),
            "device_name": _extract_device_name(raw),
            "source_url": (
                f"https://connect.garmin.com/modern/activity/{raw.get('activityId')}"
                if raw.get("activityId")
                else None
            ),
        }

        return {k: v for k, v in core.items() if v is not None}

    # ── Activity Metrics ──

    def extract_activity_metrics(
        self, summary_raw: dict, detail_raw: dict | None = None
    ) -> list[MetricRecord]:
        """activity_summaries에 없는 Garmin 메트릭 추출."""
        raw = summary_raw

        metrics = self._collect(
            # activity_summaries → metric_store 이동 (Phase 5-G)
            self._metric("calories", raw.get("calories"),
                         raw_name="calories"),
            self._metric("normalized_power", raw.get("normPower"),
                         raw_name="normPower"),
            self._metric("training_effect_aerobic",
                         raw.get("aerobicTrainingEffect"),
                         raw_name="aerobicTrainingEffect"),
            self._metric("training_effect_anaerobic",
                         raw.get("anaerobicTrainingEffect"),
                         raw_name="anaerobicTrainingEffect"),
            self._metric("training_load", raw.get("activityTrainingLoad"),
                         raw_name="activityTrainingLoad"),
            # 기존 메트릭
            self._metric("vo2max_activity", raw.get("vO2MaxValue"),
                         raw_name="vO2MaxValue"),
            self._metric("steps_activity", raw.get("steps"),
                         raw_name="steps"),
            self._metric("icu_rpe", raw.get("averageRPE"),
                         raw_name="averageRPE"),
            self._metric("body_battery_diff", raw.get("differenceBodyBattery"),
                         raw_name="differenceBodyBattery"),
            self._metric("intensity_mins_moderate",
                         raw.get("moderateIntensityMinutes"),
                         raw_name="moderateIntensityMinutes"),
            self._metric("intensity_mins_vigorous",
                         raw.get("vigorousIntensityMinutes"),
                         raw_name="vigorousIntensityMinutes"),
            self._metric("training_stress_score", raw.get("trainingStressScore"),
                         raw_name="trainingStressScore"),
            self._metric("intensity_factor", raw.get("intensityFactor"),
                         raw_name="intensityFactor"),
            self._metric("ground_contact_balance",
                         raw.get("avgGroundContactBalance"),
                         raw_name="avgGroundContactBalance"),
            self._metric("lactate_threshold_hr", raw.get("lactateThresholdBpm"),
                         raw_name="lactateThresholdBpm"),
            self._metric("lactate_threshold_speed",
                         raw.get("lactateThresholdSpeed"),
                         raw_name="lactateThresholdSpeed"),
            self._metric("performance_condition",
                         raw.get("performanceCondition"),
                         raw_name="performanceCondition"),
            self._metric("avg_respiration_rate",
                         raw.get("averageRespirationRate"),
                         raw_name="averageRespirationRate"),
            self._metric("avg_spo2", raw.get("avgSpo2"),
                         raw_name="avgSpo2"),
            self._metric("min_spo2", raw.get("minSpo2"),
                         raw_name="minSpo2"),
            self._metric(
                "timezone_offset",
                (raw.get("timeZoneUnitDTO", {}) or {}).get("offset")
                if isinstance(raw.get("timeZoneUnitDTO"), dict) else None,
                raw_name="timeZoneUnitDTO.offset",
            ),
        )

        if detail_raw:
            metrics.extend(self._extract_detail_metrics(detail_raw))

        return metrics

    def _extract_detail_metrics(self, detail: dict) -> list[MetricRecord]:
        """활동 상세 API 응답에서 추가 메트릭 추출."""
        results: list[MetricRecord] = []

        # HR Zones
        hr_zones = detail.get("hrTimeInZone") or detail.get("heartRateZones")
        if hr_zones and isinstance(hr_zones, list):
            for i, zone_data in enumerate(hr_zones[:5]):
                secs = _zone_to_seconds(zone_data)
                if secs is not None:
                    r = self._metric(
                        f"hr_zone_{i+1}_sec", secs,
                        raw_name=f"hrTimeInZone[{i}]",
                    )
                    if r:
                        results.append(r)
            r = self._metric(
                "hr_zones_detail", json_val=hr_zones,
                raw_name="hrTimeInZone",
            )
            if r:
                results.append(r)

        # Power Zones
        pz = detail.get("powerTimeInZone") or detail.get("powerZones")
        if pz and isinstance(pz, list):
            for i, zone_data in enumerate(pz[:7]):
                secs = _zone_to_seconds(zone_data)
                if secs is not None:
                    r = self._metric(
                        f"power_zone_{i+1}_sec", secs,
                        raw_name=f"powerTimeInZone[{i}]",
                    )
                    if r:
                        results.append(r)
            r = self._metric(
                "power_zones_detail", json_val=pz,
                raw_name="powerTimeInZone",
            )
            if r:
                results.append(r)

        # Weather
        weather = detail.get("weatherDTO") or detail.get("weather", {})
        if weather and isinstance(weather, dict):
            results.extend(self._collect(
                self._metric("weather_temp_c", weather.get("temp"),
                             raw_name="weatherDTO.temp"),
                self._metric("weather_humidity_pct",
                             weather.get("relativeHumidity"),
                             raw_name="weatherDTO.relativeHumidity"),
                self._metric("weather_wind_speed_ms",
                             weather.get("windSpeed"),
                             raw_name="weatherDTO.windSpeed"),
                self._metric("weather_wind_direction_deg",
                             weather.get("windDirection"),
                             raw_name="weatherDTO.windDirection"),
                self._metric("weather_dew_point_c",
                             weather.get("dewPoint"),
                             raw_name="weatherDTO.dewPoint"),
            ))

        # Splits
        splits = detail.get("splitSummaries") or detail.get("splits")
        if splits:
            r = self._metric(
                "splits_metric", json_val=splits,
                raw_name="splitSummaries",
            )
            if r:
                results.append(r)

        return results

    # ── Activity Laps ──

    def extract_activity_laps(self, splits_raw: dict) -> list[dict]:
        """Garmin `/splits` 응답(`lapDTOs`)에서 랩 추출.

        랩은 activity detail이 아니라 `get_activity_splits()` 응답에만 들어 있다.
        """
        laps_raw = splits_raw.get("lapDTOs") or splits_raw.get("laps") or []
        laps = []
        for i, lap in enumerate(laps_raw):
            avg_speed = lap.get("averageSpeed")
            lap_dict = {
                "source": self.SOURCE,
                "lap_index": i,
                "start_time": lap.get("startTimeGMT"),
                "duration_sec": _seconds(lap.get("duration")),
                "distance_m": lap.get("distance"),
                "avg_hr": _int(lap.get("averageHR")),
                "max_hr": _int(lap.get("maxHR")),
                "avg_cadence": _running_cadence(
                    lap.get("averageRunCadence")
                    or lap.get("averageRunningCadenceInStepsPerMinute")
                ),
                "avg_power": lap.get("averagePower") or lap.get("avgPower"),
                "max_power": lap.get("maxPower"),
                "elevation_gain": lap.get("elevationGain"),
                "calories": _int(lap.get("calories")),
                "lap_trigger": lap.get("intensityType") or lap.get("lapTrigger"),
            }
            if avg_speed and avg_speed > 0:
                lap_dict["avg_pace_sec_km"] = round(1000.0 / avg_speed, 2)
            laps.append({k: v for k, v in lap_dict.items() if v is not None})
        return laps

    # ── Activity Streams ──

    def extract_activity_streams(self, streams_raw: dict | list) -> list[dict]:
        """Garmin get_activity_details() → activity_streams 행 리스트.

        streams_raw 형식:
          {"metricDescriptors": [{"key": "directXxx", "metricsIndex": N}, ...],
           "activityDetailMetrics": [{"metrics": [v0, v1, ...]}, ...]}
        """
        if not isinstance(streams_raw, dict):
            return []

        descriptors = streams_raw.get("metricDescriptors", [])
        detail_metrics = streams_raw.get("activityDetailMetrics", [])
        if not descriptors or not detail_metrics:
            return []

        # Garmin 내부 key → activity_streams 타입 컬럼명
        _KEY_MAP = {
            "directElapsedDuration": "elapsed_sec",
            "directLatitude":        "latitude",
            "directLongitude":       "longitude",
            "directElevation":       "altitude_m",
            "directDistance":        "distance_m",
            "directSpeed":           "speed_ms",
            "directHeartRate":       "heart_rate",
            "directDoubleCadence":   "cadence",
            "directPower":           "power_watts",
            "directAirTemperature":  "temperature_c",
            "directTemperature":     "temperature_c",
            "directGrade":           "grade_pct",
        }

        # descriptor → 배열 인덱스 매핑
        idx_map: dict[str, int] = {}
        for d in descriptors:
            k = d.get("key") or d.get("metricsKey")
            idx = d.get("metricsIndex")
            if k is not None and idx is not None:
                idx_map[str(k)] = int(idx)

        has_elapsed = "directElapsedDuration" in idx_map
        rows: list[dict] = []

        for i, point in enumerate(detail_metrics):
            metrics = point.get("metrics", [])
            if not metrics:
                continue

            def _get(garmin_key, _m=metrics):
                pos = idx_map.get(garmin_key)
                if pos is None:
                    return None
                if isinstance(_m, list):
                    return _m[pos] if pos < len(_m) else None
                if isinstance(_m, dict):
                    return _m.get(garmin_key)
                return None

            elapsed_raw = _get("directElapsedDuration") if has_elapsed else None
            elapsed = int(elapsed_raw) if elapsed_raw is not None else i

            # directAirTemperature 우선, 없으면 directTemperature
            temp = _get("directAirTemperature")
            if temp is None:
                temp = _get("directTemperature")

            row: dict = {
                "source":      self.SOURCE,
                "elapsed_sec": elapsed,
                "latitude":    _get("directLatitude"),
                "longitude":   _get("directLongitude"),
                "altitude_m":  _get("directElevation"),
                "distance_m":  _get("directDistance"),
                "speed_ms":    _get("directSpeed"),
                "heart_rate":  _int(_get("directHeartRate")),
                "cadence":     _int(_get("directDoubleCadence")),
                "power_watts": _get("directPower"),
                "temperature_c": temp,
                "grade_pct":   _get("directGrade"),
            }
            # elapsed_sec, source는 항상 포함; 나머지 None 제거
            rows.append(
                {k: v for k, v in row.items()
                 if v is not None or k in ("elapsed_sec", "source")}
            )

        return rows

    # ── Wellness ──

    def extract_wellness_core(self, date: str, **raw_payloads) -> dict:
        """여러 Garmin wellness API → daily_wellness 핵심 필드."""
        core: dict = {"date": date}

        # Sleep — 실제 payload는 dailySleepDTO 안에 값이 있음
        sleep = raw_payloads.get("wellness_sleep", {})
        dto = sleep.get("dailySleepDTO") or {}
        if dto:
            core["sleep_score"] = _int(_score_value(dto, "overall"))
            core["sleep_duration_sec"] = _seconds(dto.get("sleepTimeSeconds"))
            core["sleep_start_time"] = _epoch_ms_to_iso(
                dto.get("sleepStartTimestampLocal")
            )

        # HRV
        hrv = raw_payloads.get("wellness_hrv", {})
        if hrv:
            summary = hrv.get("hrvSummary", hrv)
            core["hrv_weekly_avg"] = summary.get("weeklyAvg")
            core["hrv_last_night"] = summary.get("lastNightAvg")

        # Body Battery — data[0].bodyBatteryValuesArray = [[timestamp, level], ...]
        levels = _body_battery_levels(raw_payloads.get("wellness_body_battery"))
        if levels:
            core["body_battery_high"] = max(levels)
            core["body_battery_low"] = min(levels)

        # Stress
        stress = raw_payloads.get("wellness_stress", {})
        if stress:
            avg_stress = _int(stress.get("avgStressLevel"))
            core["avg_stress"] = avg_stress if avg_stress is not None and avg_stress >= 0 else None

        # User Summary — 일 최종값. resting_hr는 수면 payload 값을 보조로 사용
        summary = raw_payloads.get("wellness_user_summary", {})
        if summary:
            core["steps"] = _int(summary.get("totalSteps"))
            core["active_calories"] = _int(summary.get("activeKilocalories"))
            core["resting_hr"] = _int(summary.get("restingHeartRate"))
        if core.get("resting_hr") is None:
            core["resting_hr"] = _int(sleep.get("restingHeartRate"))

        return {k: v for k, v in core.items() if v is not None}

    def extract_wellness_metrics(
        self, date: str, **raw_payloads
    ) -> list[MetricRecord]:
        """daily_wellness core에 안 들어가는 상세 값 → metric_store."""
        metrics: list[MetricRecord] = []

        # Sleep 상세
        sleep = raw_payloads.get("wellness_sleep", {})
        dto = sleep.get("dailySleepDTO") or {}
        if dto:
            metrics.extend(self._collect(
                self._metric("sleep_deep_sec",
                             _seconds(dto.get("deepSleepSeconds")),
                             raw_name="deepSleepSeconds"),
                self._metric("sleep_light_sec",
                             _seconds(dto.get("lightSleepSeconds")),
                             raw_name="lightSleepSeconds"),
                self._metric("sleep_rem_sec",
                             _seconds(dto.get("remSleepSeconds")),
                             raw_name="remSleepSeconds"),
                self._metric("sleep_awake_sec",
                             _seconds(dto.get("awakeSleepSeconds")),
                             raw_name="awakeSleepSeconds"),
                self._metric("avg_respiration_sleep",
                             dto.get("averageRespirationValue"),
                             raw_name="averageRespirationValue"),
                self._metric("min_respiration_sleep",
                             dto.get("lowestRespirationValue"),
                             raw_name="lowestRespirationValue"),
                self._metric("avg_spo2",
                             dto.get("averageSpO2Value"),
                             raw_name="averageSpO2Value"),
                self._metric("min_spo2",
                             dto.get("lowestSpO2Value"),
                             raw_name="lowestSpO2Value"),
                self._metric("sleep_avg_hr",
                             dto.get("avgHeartRate"),
                             raw_name="avgHeartRate"),
                self._metric("sleep_body_battery_change",
                             sleep.get("bodyBatteryChange"),
                             raw_name="bodyBatteryChange"),
                self._metric("skin_temp_deviation",
                             sleep.get("avgSkinTempDeviationC"),
                             raw_name="avgSkinTempDeviationC"),
            ))

        # Stress 상세
        stress = raw_payloads.get("wellness_stress", {})
        if stress:
            metrics.extend(self._collect(
                self._metric("stress_high_duration_sec",
                             stress.get("highStressDuration"),
                             raw_name="highStressDuration"),
                self._metric("stress_medium_duration_sec",
                             stress.get("mediumStressDuration"),
                             raw_name="mediumStressDuration"),
                self._metric("stress_low_duration_sec",
                             stress.get("lowStressDuration"),
                             raw_name="lowStressDuration"),
                self._metric("stress_rest_duration_sec",
                             stress.get("restStressDuration"),
                             raw_name="restStressDuration"),
            ))

        # Training Readiness
        tr = raw_payloads.get("wellness_training_readiness", {})
        if tr:
            metrics.extend(self._collect(
                self._metric("training_readiness_score", tr.get("score"),
                             raw_name="score"),
                self._metric("training_readiness_level",
                             text=tr.get("level"),
                             raw_name="level"),
                self._metric("training_readiness_sleep_factor",
                             tr.get("sleepScoreFactorPercent"),
                             raw_name="sleepScoreFactorPercent"),
                self._metric("training_readiness_hrv_factor",
                             tr.get("hrvFactorPercent"),
                             raw_name="hrvFactorPercent"),
                self._metric("training_readiness_recovery_factor",
                             tr.get("recoveryFactorPercent"),
                             raw_name="recoveryFactorPercent"),
            ))

        # Race Predictions
        rp = raw_payloads.get("wellness_race_predictions", {})
        if rp:
            metrics.extend(self._collect(
                self._metric("race_pred_5k_sec", rp.get("raceTime5K"),
                             raw_name="raceTime5K"),
                self._metric("race_pred_10k_sec", rp.get("raceTime10K"),
                             raw_name="raceTime10K"),
                self._metric("race_pred_half_sec", rp.get("raceTimeHalf"),
                             raw_name="raceTimeHalf"),
                self._metric("race_pred_marathon_sec",
                             rp.get("raceTimeMarathon"),
                             raw_name="raceTimeMarathon"),
            ))

        # HRV 상세
        hrv = raw_payloads.get("wellness_hrv", {})
        if hrv:
            s = hrv.get("hrvSummary", hrv)
            baseline = s.get("baseline") or {}
            metrics.extend(self._collect(
                self._metric("hrv_status",
                             text=s.get("status"),
                             raw_name="status"),
                self._metric("hrv_5min_high",
                             s.get("lastNight5MinHigh"),
                             raw_name="lastNight5MinHigh"),
                self._metric("hrv_baseline_low",
                             baseline.get("lowUpper"),
                             raw_name="baseline.lowUpper"),
                self._metric("hrv_baseline_balanced_low",
                             baseline.get("balancedLow"),
                             raw_name="baseline.balancedLow"),
                self._metric("hrv_baseline_balanced_upper",
                             baseline.get("balancedUpper"),
                             raw_name="baseline.balancedUpper"),
            ))

        # User Summary extras
        summary = raw_payloads.get("wellness_user_summary", {})
        if summary:
            metrics.extend(self._collect(
                self._metric("floors_climbed",
                             summary.get("floorsAscended"),
                             raw_name="floorsAscended"),
                self._metric("calories_total",
                             summary.get("totalKilocalories"),
                             raw_name="totalKilocalories"),
            ))

        return metrics

    # ── Fitness ──

    def extract_fitness(self, date: str, raw: dict) -> dict:
        """→ daily_fitness INSERT용 dict."""
        fitness: dict = {"source": self.SOURCE, "date": date}
        vo2max = raw.get("vo2MaxValue") or raw.get("vo2max")
        if vo2max is not None:
            fitness["vo2max"] = float(vo2max)
        return {k: v for k, v in fitness.items() if v is not None}


# ── Garmin 헬퍼 함수 ──


_MAX_RUNNING_CADENCE = 250


def _running_cadence(value) -> int | None:
    """Garmin 러닝 케이던스(spm). 일부 기간(2023-10~2025-05) 원본이 양발 합산으로
    약 2배(300~420)로 오므로, 생리적 상한(250 spm)을 넘으면 절반으로 정규화한다."""
    cadence = _int(value)
    if cadence is not None and cadence > _MAX_RUNNING_CADENCE:
        return round(cadence / 2)
    return cadence


def _score_value(dto: dict, key: str):
    """dailySleepDTO.sleepScores[key] = {"value": n, "qualifierKey": ...} → n."""
    score = (dto.get("sleepScores") or {}).get(key)
    return score.get("value") if isinstance(score, dict) else None


def _epoch_ms_to_iso(value) -> str | None:
    """Garmin 로컬 epoch ms(로컬 시각을 UTC로 표기) → 'YYYY-MM-DDTHH:MM:SS'."""
    if value is None:
        return None
    return datetime.fromtimestamp(float(value) / 1000, tz=timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%S"
    )


def _body_battery_levels(payload) -> list[int]:
    """wellness_body_battery payload → 측정된 바디배터리 레벨 목록."""
    if not isinstance(payload, dict):
        return []
    days = payload.get("data")
    if not days or not isinstance(days[0], dict):
        return []
    return [
        point[1]
        for point in days[0].get("bodyBatteryValuesArray") or []
        if len(point) > 1 and point[1] is not None
    ]


def _seconds(value) -> int | None:
    """Garmin duration 값을 초 단위로 변환.
    API는 일부에서 초, 일부에서 밀리초를 반환.
    """
    if value is None:
        return None
    value = float(value)
    if value > 86400:
        return int(value / 1000)
    return int(value)


def _int(value) -> int | None:
    if value is None:
        return None
    try:
        return int(round(float(value)))
    except (ValueError, TypeError):
        return None


def _stride_to_cm(value_m) -> float | None:
    """Garmin stride length(미터 or cm) → cm 변환.
    API는 미터, ZIP은 cm일 수 있음. 0.5m 미만이면 이미 m단위가 아닌 것.
    """
    if value_m is None:
        return None
    v = float(value_m)
    if v < 5:  # 미터 단위로 추정 (stride length는 보통 0.5~2m)
        return round(v * 100, 1)
    return round(v, 1)  # 이미 cm


def _celsius_if_available(raw: dict) -> float | None:
    for key in ("avgTemperature", "averageTemperature", "minTemperature"):
        val = raw.get(key)
        if val is not None:
            return float(val)
    return None


def _extract_device_name(raw: dict) -> str | None:
    name = raw.get("deviceName")
    if name:
        return name
    meta = raw.get("metadataDTO", {})
    if isinstance(meta, dict):
        return meta.get("deviceName") or meta.get("productDisplayName")
    return None


def _best_pace(max_speed_ms) -> float | None:
    """최고 속도(m/s) → best pace (sec/km)."""
    if not max_speed_ms or max_speed_ms <= 0:
        return None
    return round(1000.0 / max_speed_ms, 2)


def _zone_to_seconds(zone_data) -> float | None:
    """HR/Power zone 데이터에서 초 추출."""
    if isinstance(zone_data, dict):
        return zone_data.get("secsInZone")
    if isinstance(zone_data, (int, float)):
        val = float(zone_data)
        return val / 1000 if val > 10000 else val
    return None
