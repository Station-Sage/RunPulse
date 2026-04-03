"""Garmin raw JSON → Layer 1 + Layer 2 변환.

Garmin API 응답 구조:
  - summary: GET /activitylist-service/activities/search/activities 의 한 항목
  - detail: GET /activity-service/activity/{id}/details
  - wellness: 여러 엔드포인트 (sleep, hrv, body_battery, stress, user_summary, etc.)
"""

from __future__ import annotations

import json
from src.sync.extractors.base import BaseExtractor, MetricRecord
from src.utils.activity_types import normalize_activity_type


class GarminExtractor(BaseExtractor):

    SOURCE = "garmin"

    # ── Activity Core ──

    def extract_activity_core(self, raw: dict) -> dict:
        """Garmin activity summary JSON → activity_summaries dict (44 cols)."""
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
            "start_time": raw.get("startTimeGMT") or raw.get("startTimeLocal"),
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
            "avg_cadence": _int(raw.get("averageRunningCadenceInStepsPerMinute")),
            "max_cadence": _int(raw.get("maxRunningCadenceInStepsPerMinute")),
            # 파워
            "avg_power": raw.get("avgPower") or raw.get("averagePower"),
            "max_power": raw.get("maxPower"),
            "normalized_power": raw.get("normPower"),
            # 고도
            "elevation_gain": raw.get("elevationGain"),
            "elevation_loss": raw.get("elevationLoss"),
            # 에너지
            "calories": _int(raw.get("calories")),
            # 훈련 효과/부하
            "training_effect_aerobic": raw.get("aerobicTrainingEffect"),
            "training_effect_anaerobic": raw.get("anaerobicTrainingEffect"),
            "training_load": raw.get("activityTrainingLoad"),
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
            # Fitness
            self._metric("vo2max_activity", raw.get("vO2MaxValue"),
                         category="fitness", raw_name="vO2MaxValue"),
            # General
            self._metric("steps_activity", raw.get("steps"),
                         category="general", raw_name="steps"),
            self._metric("perceived_exertion", raw.get("averageRPE"),
                         category="general", raw_name="averageRPE"),
            # Recovery
            self._metric("body_battery_diff", raw.get("differenceBodyBattery"),
                         category="general", raw_name="differenceBodyBattery"),
            # Training Load extras
            self._metric("intensity_mins_moderate",
                         raw.get("moderateIntensityMinutes"),
                         category="general", raw_name="moderateIntensityMinutes"),
            self._metric("intensity_mins_vigorous",
                         raw.get("vigorousIntensityMinutes"),
                         category="general", raw_name="vigorousIntensityMinutes"),
            self._metric("training_stress_score", raw.get("trainingStressScore"),
                         category="training_load", raw_name="trainingStressScore"),
            self._metric("intensity_factor", raw.get("intensityFactor"),
                         category="training_load", raw_name="intensityFactor"),
            # Running Dynamics extra
            self._metric("ground_contact_balance",
                         raw.get("avgGroundContactBalance"),
                         category="running_dynamics",
                         raw_name="avgGroundContactBalance"),
            # Fitness extras
            self._metric("lactate_threshold_hr", raw.get("lactateThresholdBpm"),
                         category="threshold", raw_name="lactateThresholdBpm"),
            self._metric("lactate_threshold_speed",
                         raw.get("lactateThresholdSpeed"),
                         category="threshold", raw_name="lactateThresholdSpeed"),
            self._metric("performance_condition",
                         raw.get("performanceCondition"),
                         category="fitness", raw_name="performanceCondition"),
            # Respiration
            self._metric("avg_respiration_rate",
                         raw.get("averageRespirationRate"),
                         category="running_dynamics",
                         raw_name="averageRespirationRate"),
            # SpO2
            self._metric("avg_spo2", raw.get("avgSpo2"),
                         category="fitness", raw_name="avgSpo2"),
            self._metric("min_spo2", raw.get("minSpo2"),
                         category="fitness", raw_name="minSpo2"),
            # Meta
            self._metric(
                "timezone_offset",
                (raw.get("timeZoneUnitDTO", {}) or {}).get("offset")
                if isinstance(raw.get("timeZoneUnitDTO"), dict) else None,
                category="general", raw_name="timeZoneUnitDTO.offset",
            ),
            self._metric("best_pace_sec_km", _best_pace(raw.get("maxSpeed")),
                         category="general", raw_name="maxSpeed→best_pace"),
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
                        category="hr_zone",
                        raw_name=f"hrTimeInZone[{i}]",
                    )
                    if r:
                        results.append(r)
            r = self._metric(
                "hr_zones_detail", json_val=hr_zones,
                category="hr_zone", raw_name="hrTimeInZone",
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
                        category="power_zone",
                        raw_name=f"powerTimeInZone[{i}]",
                    )
                    if r:
                        results.append(r)
            r = self._metric(
                "power_zones_detail", json_val=pz,
                category="power_zone", raw_name="powerTimeInZone",
            )
            if r:
                results.append(r)

        # Weather
        weather = detail.get("weatherDTO") or detail.get("weather", {})
        if weather and isinstance(weather, dict):
            results.extend(self._collect(
                self._metric("weather_temp_c", weather.get("temp"),
                             category="weather", raw_name="weatherDTO.temp"),
                self._metric("weather_humidity_pct",
                             weather.get("relativeHumidity"),
                             category="weather",
                             raw_name="weatherDTO.relativeHumidity"),
                self._metric("weather_wind_speed_ms",
                             weather.get("windSpeed"),
                             category="weather",
                             raw_name="weatherDTO.windSpeed"),
                self._metric("weather_wind_direction_deg",
                             weather.get("windDirection"),
                             category="weather",
                             raw_name="weatherDTO.windDirection"),
                self._metric("weather_dew_point_c",
                             weather.get("dewPoint"),
                             category="weather",
                             raw_name="weatherDTO.dewPoint"),
            ))

        # Splits
        splits = detail.get("splitSummaries") or detail.get("splits")
        if splits:
            r = self._metric(
                "splits_metric", json_val=splits,
                category="general", raw_name="splitSummaries",
            )
            if r:
                results.append(r)

        return results

    # ── Activity Laps ──

    def extract_activity_laps(self, detail_raw: dict) -> list[dict]:
        """Garmin 상세 API에서 랩 추출."""
        laps_raw = detail_raw.get("laps") or detail_raw.get("lapDTOs") or []
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
                "avg_cadence": _int(
                    lap.get("averageRunningCadenceInStepsPerMinute")
                ),
                "avg_power": lap.get("avgPower"),
                "max_power": lap.get("maxPower"),
                "elevation_gain": lap.get("elevationGain"),
                "calories": _int(lap.get("calories")),
                "lap_trigger": lap.get("lapTrigger"),
            }
            if avg_speed and avg_speed > 0:
                lap_dict["avg_pace_sec_km"] = round(1000.0 / avg_speed, 2)
            laps.append({k: v for k, v in lap_dict.items() if v is not None})
        return laps

    # ── Wellness ──

    def extract_wellness_core(self, date: str, **raw_payloads) -> dict:
        """여러 Garmin wellness API → daily_wellness 핵심 필드."""
        core: dict = {"date": date}

        # Sleep
        sleep = raw_payloads.get("sleep_day", {})
        if sleep:
            core["sleep_score"] = _int(
                sleep.get("overallScore")
                or (sleep.get("sleepScores") or {}).get("overall")
            )
            core["sleep_duration_sec"] = _seconds(
                sleep.get("sleepTimeSeconds")
            )
            core["sleep_start_time"] = (
                sleep.get("sleepStartTimestampGMT")
                or sleep.get("calendarDate")
            )

        # HRV
        hrv = raw_payloads.get("hrv_day", {})
        if hrv:
            summary = hrv.get("hrvSummary", hrv)
            core["hrv_weekly_avg"] = summary.get("weeklyAvg")
            core["hrv_last_night"] = (
                summary.get("lastNightAvg")
                or summary.get("lastNight5MinHigh")
            )
            core["resting_hr"] = _int(summary.get("restingHeartRate"))

        # Body Battery
        bb = raw_payloads.get("body_battery_day", {})
        if bb:
            if isinstance(bb, list) and bb:
                values = [
                    item.get("bodyBatteryLevel", 0)
                    for item in bb
                    if item.get("bodyBatteryLevel") is not None
                ]
                if values:
                    core["body_battery_high"] = max(values)
                    core["body_battery_low"] = min(values)
            elif isinstance(bb, dict):
                core["body_battery_high"] = (
                    bb.get("bodyBatteryHigh") or bb.get("highestValue")
                )
                core["body_battery_low"] = (
                    bb.get("bodyBatteryLow") or bb.get("lowestValue")
                )

        # Stress
        stress = raw_payloads.get("stress_day", {})
        if stress:
            core["avg_stress"] = _int(
                stress.get("overallStressLevel")
                or stress.get("avgStressLevel")
            )

        # User Summary
        summary = raw_payloads.get("user_summary_day", {})
        if summary:
            core["steps"] = _int(summary.get("totalSteps"))
            core["active_calories"] = _int(
                summary.get("activeKilocalories")
            )
            if "resting_hr" not in core or core.get("resting_hr") is None:
                core["resting_hr"] = _int(summary.get("restingHeartRate"))

        return {k: v for k, v in core.items() if v is not None}

    def extract_wellness_metrics(
        self, date: str, **raw_payloads
    ) -> list[MetricRecord]:
        """daily_wellness core에 안 들어가는 상세 값 → metric_store."""
        metrics: list[MetricRecord] = []

        # Sleep 상세
        sleep = raw_payloads.get("sleep_day", {})
        if sleep:
            metrics.extend(self._collect(
                self._metric("sleep_deep_sec",
                             _seconds(sleep.get("deepSleepSeconds")),
                             category="sleep", raw_name="deepSleepSeconds"),
                self._metric("sleep_light_sec",
                             _seconds(sleep.get("lightSleepSeconds")),
                             category="sleep", raw_name="lightSleepSeconds"),
                self._metric("sleep_rem_sec",
                             _seconds(sleep.get("remSleepSeconds")),
                             category="sleep", raw_name="remSleepSeconds"),
                self._metric("sleep_awake_sec",
                             _seconds(sleep.get("awakeSleepSeconds")),
                             category="sleep", raw_name="awakeSleepSeconds"),
                self._metric("avg_respiration_sleep",
                             sleep.get("averageRespiration"),
                             category="sleep", raw_name="averageRespiration"),
                self._metric("avg_spo2",
                             sleep.get("averageSpO2Value"),
                             category="sleep", raw_name="averageSpO2Value"),
                self._metric("sleep_deep_score",
                             (sleep.get("sleepScores") or {}).get("deep"),
                             category="sleep", raw_name="sleepScores.deep"),
                self._metric("sleep_rem_score",
                             (sleep.get("sleepScores") or {}).get("rem"),
                             category="sleep", raw_name="sleepScores.rem"),
                self._metric("sleep_recovery_score",
                             (sleep.get("sleepScores") or {}).get("recovery"),
                             category="sleep",
                             raw_name="sleepScores.recovery"),
            ))

        # Stress 상세
        stress = raw_payloads.get("stress_day", {})
        if stress:
            metrics.extend(self._collect(
                self._metric("stress_high_duration_sec",
                             stress.get("highStressDuration"),
                             category="stress",
                             raw_name="highStressDuration"),
                self._metric("stress_medium_duration_sec",
                             stress.get("mediumStressDuration"),
                             category="stress",
                             raw_name="mediumStressDuration"),
                self._metric("stress_low_duration_sec",
                             stress.get("lowStressDuration"),
                             category="stress",
                             raw_name="lowStressDuration"),
                self._metric("stress_rest_duration_sec",
                             stress.get("restStressDuration"),
                             category="stress",
                             raw_name="restStressDuration"),
            ))

        # Training Readiness
        tr = raw_payloads.get("training_readiness", {})
        if tr:
            metrics.extend(self._collect(
                self._metric("training_readiness_score", tr.get("score"),
                             category="readiness", raw_name="score"),
                self._metric("training_readiness_level",
                             text=tr.get("level"),
                             category="readiness", raw_name="level"),
                self._metric("training_readiness_sleep_factor",
                             tr.get("sleepScoreFactorPercent"),
                             category="readiness",
                             raw_name="sleepScoreFactorPercent"),
                self._metric("training_readiness_hrv_factor",
                             tr.get("hrvFactorPercent"),
                             category="readiness",
                             raw_name="hrvFactorPercent"),
                self._metric("training_readiness_recovery_factor",
                             tr.get("recoveryFactorPercent"),
                             category="readiness",
                             raw_name="recoveryFactorPercent"),
            ))

        # Race Predictions
        rp = raw_payloads.get("race_predictions", {})
        if rp:
            metrics.extend(self._collect(
                self._metric("race_pred_5k_sec", rp.get("raceTime5K"),
                             category="prediction", raw_name="raceTime5K"),
                self._metric("race_pred_10k_sec", rp.get("raceTime10K"),
                             category="prediction", raw_name="raceTime10K"),
                self._metric("race_pred_half_sec", rp.get("raceTimeHalf"),
                             category="prediction", raw_name="raceTimeHalf"),
                self._metric("race_pred_marathon_sec",
                             rp.get("raceTimeMarathon"),
                             category="prediction",
                             raw_name="raceTimeMarathon"),
            ))

        # HRV 상세
        hrv = raw_payloads.get("hrv_day", {})
        if hrv:
            s = hrv.get("hrvSummary", hrv)
            metrics.extend(self._collect(
                self._metric("hrv_7d_avg", s.get("weeklyAvg"),
                             category="fitness", raw_name="weeklyAvg"),
                self._metric("hrv_status",
                             text=s.get("status") or s.get("hrvStatus"),
                             category="fitness", raw_name="status"),
                self._metric("hrv_baseline_low",
                             s.get("baselineLowUpper"),
                             category="fitness",
                             raw_name="baselineLowUpper"),
                self._metric("hrv_baseline_balanced_low",
                             s.get("baselineBalancedLow"),
                             category="fitness",
                             raw_name="baselineBalancedLow"),
                self._metric("hrv_baseline_balanced_upper",
                             s.get("baselineBalancedUpper"),
                             category="fitness",
                             raw_name="baselineBalancedUpper"),
            ))

        # User Summary extras
        summary = raw_payloads.get("user_summary_day", {})
        if summary:
            metrics.extend(self._collect(
                self._metric("floors_climbed",
                             summary.get("floorsAscended"),
                             category="general",
                             raw_name="floorsAscended"),
                self._metric("total_calories",
                             summary.get("totalKilocalories"),
                             category="general",
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
