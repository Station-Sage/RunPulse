"""Strava raw JSON → Layer 1 + Layer 2 변환."""

from __future__ import annotations

import json
from src.sync.extractors.base import BaseExtractor, MetricRecord
from src.utils.activity_types import normalize_activity_type


class StravaExtractor(BaseExtractor):

    SOURCE = "strava"

    def extract_activity_core(self, raw: dict) -> dict:
        avg_speed = raw.get("average_speed")
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
            "start_time": raw.get("start_date"),
            "distance_m": raw.get("distance"),
            "duration_sec": raw.get("elapsed_time"),
            "moving_time_sec": raw.get("moving_time"),
            "elapsed_time_sec": raw.get("elapsed_time"),
            "avg_speed_ms": avg_speed,
            "max_speed_ms": raw.get("max_speed"),
            "avg_pace_sec_km": avg_pace,
            "avg_hr": _int(raw.get("average_heartrate")),
            "max_hr": _int(raw.get("max_heartrate")),
            "avg_cadence": _int(raw.get("average_cadence")),
            "avg_power": raw.get("average_watts") or raw.get("weighted_average_watts"),
            "max_power": raw.get("max_watts"),
            "normalized_power": raw.get("weighted_average_watts"),
            "elevation_gain": raw.get("total_elevation_gain"),
            "calories": _int(raw.get("calories")),
            "suffer_score": _int(raw.get("suffer_score")),
            "start_lat": _latlng_idx(raw.get("start_latlng"), 0),
            "start_lon": _latlng_idx(raw.get("start_latlng"), 1),
            "end_lat": _latlng_idx(raw.get("end_latlng"), 0),
            "end_lon": _latlng_idx(raw.get("end_latlng"), 1),
            "avg_temperature": raw.get("average_temp"),
            "description": raw.get("description"),
            "event_type": raw.get("workout_type"),
            "device_name": raw.get("device_name"),
            "gear_id": raw.get("gear_id"),
            "source_url": (
                f"https://www.strava.com/activities/{raw.get('id')}"
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
            self._metric("kilojoules", raw.get("kilojoules"),
                         category="general", raw_name="kilojoules"),
            self._metric("perceived_exertion",
                         raw.get("perceived_exertion"),
                         category="general",
                         raw_name="perceived_exertion"),
            self._metric("achievement_count",
                         raw.get("achievement_count"),
                         category="social", raw_name="achievement_count"),
            self._metric("pr_count", raw.get("pr_count"),
                         category="social", raw_name="pr_count"),
            self._metric("kudos_count", raw.get("kudos_count"),
                         category="social", raw_name="kudos_count"),
            # normalized_power 삭제 — activity_summaries 컬럼과 중복 (이중 저장 금지 원칙)
            self._metric("timezone_offset",
                         text=raw.get("timezone"),
                         category="general", raw_name="timezone"),
        )

        # Segment Efforts
        if raw.get("segment_efforts"):
            r = self._metric(
                "segment_efforts",
                json_val=_simplify_segments(raw["segment_efforts"]),
                category="general", raw_name="segment_efforts",
            )
            if r:
                metrics.append(r)

        # Splits
        if raw.get("splits_metric"):
            r = self._metric(
                "splits_metric", json_val=raw["splits_metric"],
                category="general", raw_name="splits_metric",
            )
            if r:
                metrics.append(r)

        return metrics

    def extract_activity_streams(
        self, streams_raw: dict | list
    ) -> list[dict]:
        """Strava streams API → activity_streams dict 리스트."""
        if isinstance(streams_raw, list):
            stream_map = {
                s["type"]: s["data"]
                for s in streams_raw
                if "type" in s and "data" in s
            }
        elif isinstance(streams_raw, dict):
            stream_map = {
                k: v.get("data", v) if isinstance(v, dict) else v
                for k, v in streams_raw.items()
            }
        else:
            return []

        time_data = stream_map.get("time", [])
        if not time_data:
            return []

        latlng_data = stream_map.get("latlng", [])
        rows = []
        for i, t in enumerate(time_data):
            row = {
                "source": self.SOURCE,
                "elapsed_sec": t,
                "distance_m": _safe_idx(stream_map.get("distance"), i),
                "heart_rate": _safe_idx(stream_map.get("heartrate"), i),
                "cadence": _safe_idx(stream_map.get("cadence"), i),
                "power_watts": _safe_idx(stream_map.get("watts"), i),
                "altitude_m": _safe_idx(stream_map.get("altitude"), i),
                "speed_ms": _safe_idx(
                    stream_map.get("velocity_smooth"), i
                ),
                "latitude": (
                    latlng_data[i][0]
                    if i < len(latlng_data) and isinstance(latlng_data[i], (list, tuple)) and len(latlng_data[i]) >= 2
                    else None
                ),
                "longitude": (
                    latlng_data[i][1]
                    if i < len(latlng_data) and isinstance(latlng_data[i], (list, tuple)) and len(latlng_data[i]) >= 2
                    else None
                ),
                "grade_pct": _safe_idx(stream_map.get("grade_smooth"), i),
                "temperature_c": _safe_idx(stream_map.get("temp"), i),
            }
            rows.append({k: v for k, v in row.items() if v is not None})
        return rows

    def extract_best_efforts(self, raw: dict) -> list[dict]:
        efforts = raw.get("best_efforts", [])
        results = []
        for e in efforts:
            results.append({
                "source": self.SOURCE,
                "effort_name": e.get("name", "unknown"),
                "elapsed_sec": e.get("elapsed_time"),
                "distance_m": e.get("distance"),
                "start_index": e.get("start_index"),
                "end_index": e.get("end_index"),
                "pr_rank": e.get("pr_rank"),
            })
        return results


# ── Strava 헬퍼 ──


def _int(value) -> int | None:
    if value is None:
        return None
    try:
        return int(round(float(value)))
    except (ValueError, TypeError):
        return None


def _latlng_idx(latlng, idx: int) -> float | None:
    if isinstance(latlng, (list, tuple)) and len(latlng) > idx:
        return latlng[idx]
    return None


def _safe_idx(lst, i):
    if lst is None or i >= len(lst):
        return None
    return lst[i]


def _simplify_segments(segments: list) -> list:
    return [
        {
            "name": s.get("name"),
            "elapsed_time": s.get("elapsed_time"),
            "distance": s.get("distance"),
            "average_hr": s.get("average_heartrate"),
            "pr_rank": s.get("pr_rank"),
        }
        for s in segments[:20]
    ]
