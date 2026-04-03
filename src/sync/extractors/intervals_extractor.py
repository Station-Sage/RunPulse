"""Intervals.icu raw JSON → Layer 1 + Layer 2 변환."""

from __future__ import annotations

import json
from src.sync.extractors.base import BaseExtractor, MetricRecord
from src.utils.activity_types import normalize_activity_type


class IntervalsExtractor(BaseExtractor):

    SOURCE = "intervals"

    def extract_activity_core(self, raw: dict) -> dict:
        avg_speed = raw.get("average_speed")
        if avg_speed is None and raw.get("distance") and raw.get("moving_time"):
            d = raw["distance"]
            t = raw["moving_time"]
            avg_speed = d / t if t > 0 else None

        avg_pace = (
            round(1000.0 / avg_speed, 2)
            if avg_speed and avg_speed > 0
            else None
        )

        core = {
            "source": self.SOURCE,
            "source_id": str(raw.get("id", "")),
            "name": raw.get("name"),
            "activity_type": normalize_activity_type(
                raw.get("type", "unknown"), self.SOURCE
            ),
            "start_time": raw.get("start_date_local") or raw.get("start_date"),
            "distance_m": raw.get("distance"),
            "duration_sec": raw.get("elapsed_time") or raw.get("icu_total_time"),
            "moving_time_sec": raw.get("moving_time") or raw.get("icu_moving_time"),
            "elapsed_time_sec": raw.get("elapsed_time"),
            "avg_speed_ms": avg_speed,
            "max_speed_ms": raw.get("max_speed"),
            "avg_pace_sec_km": avg_pace,
            "avg_hr": _int(raw.get("average_heartrate") or raw.get("icu_average_hr")),
            "max_hr": _int(raw.get("max_heartrate") or raw.get("icu_max_hr")),
            "avg_cadence": _int(raw.get("avg_run_cadence") or raw.get("average_cadence")),
            "avg_power": raw.get("icu_weighted_avg_watts") or raw.get("average_watts"),
            "max_power": raw.get("max_watts") or raw.get("icu_max_watts"),
            "normalized_power": raw.get("icu_weighted_avg_watts"),
            "elevation_gain": raw.get("total_elevation_gain"),
            "elevation_loss": raw.get("total_elevation_loss"),
            "calories": _int(raw.get("calories") or raw.get("icu_calories")),
            "training_load": raw.get("icu_training_load"),
            "avg_stride_length_cm": _stride_cm(raw.get("average_stride")),
            "start_lat": raw.get("start_latlng", [None, None])[0] if isinstance(raw.get("start_latlng"), list) and len(raw.get("start_latlng", [])) >= 2 else None,
            "start_lon": raw.get("start_latlng", [None, None])[1] if isinstance(raw.get("start_latlng"), list) and len(raw.get("start_latlng", [])) >= 2 else None,
            "avg_temperature": raw.get("icu_average_temp") or raw.get("average_temp"),
            "description": raw.get("description"),
            "event_type": raw.get("workout_type"),
            "device_name": raw.get("device_name"),
            "gear_id": raw.get("gear_id"),
            "source_url": (
                f"https://intervals.icu/activities/{raw.get('id')}"
                if raw.get("id")
                else None
            ),
        }
        return {k: v for k, v in core.items() if v is not None}

    def extract_activity_metrics(
        self, summary_raw: dict, detail_raw: dict | None = None
    ) -> list[MetricRecord]:
        raw = detail_raw or summary_raw

        metrics = self._collect(
            # Training Load
            self._metric("trimp", raw.get("icu_trimp"),
                         category="training_load", raw_name="icu_trimp"),
            self._metric("hrss", raw.get("icu_hrss"),
                         category="training_load", raw_name="icu_hrss"),
            # Efficiency
            self._metric("efficiency_factor",
                         raw.get("icu_efficiency_factor"),
                         category="efficiency",
                         raw_name="icu_efficiency_factor"),
            self._metric("aerobic_decoupling",
                         raw.get("icu_decoupling"),
                         category="efficiency",
                         raw_name="icu_decoupling"),
            self._metric("variability_index",
                         raw.get("icu_variability_index"),
                         category="efficiency",
                         raw_name="icu_variability_index"),
            # Power
            self._metric("icu_ftp", raw.get("icu_ftp"),
                         category="power", raw_name="icu_ftp"),
            # Pace
            self._metric("gap", raw.get("icu_gap"),
                         category="fitness", raw_name="icu_gap"),
            # Perception
            self._metric("icu_rpe", raw.get("icu_rpe"),
                         category="perception", raw_name="icu_rpe"),
            self._metric("icu_feel", raw.get("icu_feel"),
                         category="perception", raw_name="icu_feel"),
        )

        # HR Zone times (JSON)
        hr_zones = raw.get("icu_hr_zone_times")
        if hr_zones and isinstance(hr_zones, list):
            for i, secs in enumerate(hr_zones[:5]):
                if secs is not None:
                    r = self._metric(
                        f"hr_zone_{i+1}_sec", secs,
                        category="hr_zone",
                        raw_name=f"icu_hr_zone_times[{i}]",
                    )
                    if r:
                        metrics.append(r)
            r = self._metric(
                "hr_zones_detail", json_val=hr_zones,
                category="hr_zone", raw_name="icu_hr_zone_times",
            )
            if r:
                metrics.append(r)

        # Power curve
        if raw.get("icu_power_curve"):
            r = self._metric(
                "power_curve", json_val=raw["icu_power_curve"],
                category="power", raw_name="icu_power_curve",
            )
            if r:
                metrics.append(r)

        # Weather
        for field, metric in [
            ("icu_weather_temp", "weather_temp_c"),
            ("icu_weather_humidity", "weather_humidity_pct"),
            ("icu_weather_wind_speed", "weather_wind_speed_ms"),
        ]:
            val = raw.get(field)
            if val is not None:
                r = self._metric(metric, val,
                                 category="weather", raw_name=field)
                if r:
                    metrics.append(r)

        return metrics

    # ── Wellness ──

    def extract_wellness_core(self, date: str, **raw_payloads) -> dict:
        """Intervals.icu wellness → daily_wellness dict."""
        raw = raw_payloads.get("wellness", {})
        if not raw:
            return {}

        core = {"date": date}
        mapping = {
            "sleepQuality": "sleep_score",
            "sleepSecs": "sleep_duration_sec",
            "hrv": "hrv_last_night",
            "restingHR": "resting_hr",
            "weight": "weight_kg",
            "steps": "steps",
        }
        for src_key, db_key in mapping.items():
            val = raw.get(src_key)
            if val is not None:
                core[db_key] = val

        return {k: v for k, v in core.items() if v is not None}

    def extract_fitness(self, date: str, raw: dict) -> dict:
        """Intervals.icu fitness → daily_fitness dict."""
        fitness = {"source": self.SOURCE, "date": date}
        for src_key, db_key in [
            ("ctl", "ctl"), ("atl", "atl"), ("tsb", "tsb"),
            ("rampRate", "ramp_rate"),
        ]:
            val = raw.get(src_key)
            if val is not None:
                fitness[db_key] = float(val)
        return {k: v for k, v in fitness.items() if v is not None}


# ── 헬퍼 ──

def _int(value) -> int | None:
    if value is None:
        return None
    try:
        return int(round(float(value)))
    except (ValueError, TypeError):
        return None


def _stride_cm(value) -> float | None:
    """Intervals stride (m) → cm."""
    if value is None:
        return None
    v = float(value)
    return round(v * 100, 1) if v < 5 else round(v, 1)
