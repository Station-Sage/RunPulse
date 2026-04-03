"""Runalyze raw JSON → Layer 1 + Layer 2 변환."""

from __future__ import annotations

from src.sync.extractors.base import BaseExtractor, MetricRecord
from src.utils.activity_types import normalize_activity_type


class RunalyzeExtractor(BaseExtractor):

    SOURCE = "runalyze"

    def extract_activity_core(self, raw: dict) -> dict:
        distance_m = raw.get("distance")
        if distance_m is None and raw.get("distance_km"):
            distance_m = raw["distance_km"] * 1000

        duration_sec = raw.get("s") or raw.get("duration")
        avg_pace = None
        if distance_m and distance_m > 0 and duration_sec:
            avg_pace = round(duration_sec / (distance_m / 1000), 2)

        avg_speed = None
        if distance_m and duration_sec and duration_sec > 0:
            avg_speed = distance_m / duration_sec

        core = {
            "source": self.SOURCE,
            "source_id": str(raw.get("id", "")),
            "name": raw.get("title") or raw.get("name"),
            "activity_type": normalize_activity_type(
                raw.get("sport", {}).get("name", "unknown")
                if isinstance(raw.get("sport"), dict)
                else str(raw.get("sport", "unknown")),
                self.SOURCE,
            ),
            "start_time": raw.get("datetime") or raw.get("start_time"),
            "distance_m": distance_m,
            "duration_sec": _int(duration_sec),
            "moving_time_sec": _int(raw.get("elapsed_time")),
            "avg_speed_ms": avg_speed,
            "avg_pace_sec_km": avg_pace,
            "avg_hr": _int(raw.get("pulse_avg") or raw.get("avg_hr")),
            "max_hr": _int(raw.get("pulse_max") or raw.get("max_hr")),
            "avg_cadence": _int(raw.get("cadence")),
            "avg_power": raw.get("power"),
            "elevation_gain": raw.get("elevation") or raw.get("elevation_gain"),
            "calories": _int(raw.get("kcal") or raw.get("calories")),
            "training_load": raw.get("trimp"),
            "avg_temperature": raw.get("temperature"),
            "description": raw.get("notes"),
            "source_url": (
                f"https://runalyze.com/activity/{raw.get('id')}"
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
            self._metric("effective_vo2max", raw.get("vo2max"),
                         category="fitness", raw_name="vo2max"),
            self._metric("vdot", raw.get("vdot"),
                         category="fitness", raw_name="vdot"),
            self._metric("marathon_shape", raw.get("marathonShape"),
                         category="fitness", raw_name="marathonShape"),
            self._metric("trimp", raw.get("trimp"),
                         category="training_load", raw_name="trimp"),
        )

        # Race Predictions
        preds = raw.get("racePredictions") or raw.get("predictions", {})
        if preds and isinstance(preds, dict):
            metrics.extend(self._collect(
                self._metric("race_pred_5k_sec", preds.get("5k"),
                             category="prediction", raw_name="predictions.5k"),
                self._metric("race_pred_10k_sec", preds.get("10k"),
                             category="prediction", raw_name="predictions.10k"),
                self._metric("race_pred_half_sec", preds.get("half"),
                             category="prediction",
                             raw_name="predictions.half"),
                self._metric("race_pred_marathon_sec",
                             preds.get("marathon") or preds.get("full"),
                             category="prediction",
                             raw_name="predictions.marathon"),
            ))

        return metrics


def _int(value) -> int | None:
    if value is None:
        return None
    try:
        return int(round(float(value)))
    except (ValueError, TypeError):
        return None
