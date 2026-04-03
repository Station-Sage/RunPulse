"""Garmin Extractor 단위 테스트."""

import json
import pytest
from pathlib import Path
from src.sync.extractors.garmin_extractor import GarminExtractor


FIXTURES = Path(__file__).parent / "fixtures" / "api" / "garmin"


@pytest.fixture
def ext():
    return GarminExtractor()


@pytest.fixture
def summary_raw():
    with open(FIXTURES / "activity_summary_minimal.json") as f:
        return json.load(f)


@pytest.fixture
def detail_raw():
    with open(FIXTURES / "activity_detail_minimal.json") as f:
        return json.load(f)


@pytest.fixture
def wellness_raw():
    with open(FIXTURES / "wellness_minimal.json") as f:
        return json.load(f)


class TestGarminActivityCore:
    def test_required_fields(self, ext, summary_raw):
        core = ext.extract_activity_core(summary_raw)
        assert core["source"] == "garmin"
        assert core["source_id"] == "12345678901"
        assert core["activity_type"] == "running"
        assert core["start_time"] is not None

    def test_distance_and_time(self, ext, summary_raw):
        core = ext.extract_activity_core(summary_raw)
        assert core["distance_m"] == 10020.0
        assert core["duration_sec"] == 3120
        assert core["moving_time_sec"] == 3050

    def test_pace_calculated(self, ext, summary_raw):
        core = ext.extract_activity_core(summary_raw)
        assert core["avg_pace_sec_km"] == round(1000.0 / 3.212, 2)

    def test_heart_rate(self, ext, summary_raw):
        core = ext.extract_activity_core(summary_raw)
        assert core["avg_hr"] == 155
        assert core["max_hr"] == 178

    def test_training_effects(self, ext, summary_raw):
        core = ext.extract_activity_core(summary_raw)
        assert core["training_effect_aerobic"] == 3.2
        assert core["training_effect_anaerobic"] == 1.1
        assert core["training_load"] == 85.5

    def test_running_dynamics(self, ext, summary_raw):
        core = ext.extract_activity_core(summary_raw)
        assert core["avg_ground_contact_time_ms"] == 235.0
        # avgStrideLength=1.12m → 112.0cm
        assert core["avg_stride_length_cm"] == 112.0

    def test_location(self, ext, summary_raw):
        core = ext.extract_activity_core(summary_raw)
        assert abs(core["start_lat"] - 37.5665) < 0.001
        assert abs(core["start_lon"] - 126.978) < 0.001

    def test_no_none_values(self, ext, summary_raw):
        core = ext.extract_activity_core(summary_raw)
        for k, v in core.items():
            assert v is not None, f"key '{k}' should not be None"

    def test_source_url(self, ext, summary_raw):
        core = ext.extract_activity_core(summary_raw)
        assert "12345678901" in core["source_url"]

    def test_empty_input_returns_minimal(self, ext):
        core = ext.extract_activity_core({})
        assert core["source"] == "garmin"
        assert "activity_type" in core


class TestGarminActivityMetrics:
    def test_basic_metrics(self, ext, summary_raw):
        metrics = ext.extract_activity_metrics(summary_raw)
        names = {m.metric_name for m in metrics}
        assert "vo2max_activity" in names
        assert "steps_activity" in names
        assert "body_battery_diff" in names

    def test_no_empty_metrics(self, ext, summary_raw):
        metrics = ext.extract_activity_metrics(summary_raw)
        for m in metrics:
            assert not m.is_empty()

    def test_detail_hr_zones(self, ext, summary_raw, detail_raw):
        metrics = ext.extract_activity_metrics(summary_raw, detail_raw)
        names = {m.metric_name for m in metrics}
        assert "hr_zone_1_sec" in names
        assert "hr_zones_detail" in names

    def test_detail_weather(self, ext, summary_raw, detail_raw):
        metrics = ext.extract_activity_metrics(summary_raw, detail_raw)
        names = {m.metric_name for m in metrics}
        assert "weather_temp_c" in names
        assert "weather_humidity_pct" in names

    def test_no_core_duplicates(self, ext, summary_raw):
        """activity_summaries에 있는 필드가 metric에 중복되면 안 됨."""
        metrics = ext.extract_activity_metrics(summary_raw)
        core_fields = {"avg_hr", "max_hr", "distance_m", "duration_sec",
                        "training_effect_aerobic", "calories"}
        metric_names = {m.metric_name for m in metrics}
        assert metric_names.isdisjoint(core_fields)


class TestGarminLaps:
    def test_lap_extraction(self, ext, detail_raw):
        laps = ext.extract_activity_laps(detail_raw)
        assert len(laps) == 2
        assert laps[0]["lap_index"] == 0
        assert laps[0]["source"] == "garmin"
        assert laps[0]["distance_m"] == 1000.0

    def test_lap_pace_calculated(self, ext, detail_raw):
        laps = ext.extract_activity_laps(detail_raw)
        assert "avg_pace_sec_km" in laps[0]
        assert laps[0]["avg_pace_sec_km"] > 0

    def test_empty_detail(self, ext):
        assert ext.extract_activity_laps({}) == []


class TestGarminWellness:
    def test_wellness_core(self, ext, wellness_raw):
        core = ext.extract_wellness_core("2025-03-25", **wellness_raw)
        assert core["date"] == "2025-03-25"
        assert core["sleep_score"] == 82
        assert core["resting_hr"] == 52
        assert core["body_battery_high"] == 95
        assert core["body_battery_low"] == 25
        assert core["steps"] == 12500

    def test_wellness_metrics(self, ext, wellness_raw):
        metrics = ext.extract_wellness_metrics("2025-03-25", **wellness_raw)
        names = {m.metric_name for m in metrics}
        assert "sleep_deep_sec" in names
        assert "training_readiness_score" in names
        assert "race_pred_5k_sec" in names
        assert "stress_high_duration_sec" in names

    def test_wellness_metric_values(self, ext, wellness_raw):
        metrics = ext.extract_wellness_metrics("2025-03-25", **wellness_raw)
        by_name = {m.metric_name: m for m in metrics}
        assert by_name["training_readiness_score"].numeric_value == 72
        assert by_name["race_pred_5k_sec"].numeric_value == 1200

    def test_fitness(self, ext):
        raw = {"vo2MaxValue": 52.0}
        fit = ext.extract_fitness("2025-03-25", raw)
        assert fit["source"] == "garmin"
        assert fit["vo2max"] == 52.0
