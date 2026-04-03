"""Intervals.icu Extractor 단위 테스트."""

import json
import pytest
from pathlib import Path
from src.sync.extractors.intervals_extractor import IntervalsExtractor


FIXTURES = Path(__file__).parent / "fixtures" / "api" / "intervals"


@pytest.fixture
def ext():
    return IntervalsExtractor()


@pytest.fixture
def activity_raw():
    with open(FIXTURES / "activity_minimal.json") as f:
        return json.load(f)


@pytest.fixture
def wellness_raw():
    with open(FIXTURES / "wellness_minimal.json") as f:
        return json.load(f)


class TestIntervalsActivityCore:
    def test_required_fields(self, ext, activity_raw):
        core = ext.extract_activity_core(activity_raw)
        assert core["source"] == "intervals"
        assert core["source_id"] == "i2025032501"
        assert core["activity_type"] == "running"

    def test_distance_time(self, ext, activity_raw):
        core = ext.extract_activity_core(activity_raw)
        assert core["distance_m"] == 10030.0
        assert core["duration_sec"] == 3130

    def test_stride_length_converted(self, ext, activity_raw):
        core = ext.extract_activity_core(activity_raw)
        # 1.13m → 113.0cm
        assert core["avg_stride_length_cm"] == 113.0

    def test_training_load(self, ext, activity_raw):
        core = ext.extract_activity_core(activity_raw)
        assert core["training_load"] == 84.2


class TestIntervalsActivityMetrics:
    def test_training_metrics(self, ext, activity_raw):
        metrics = ext.extract_activity_metrics(activity_raw)
        names = {m.metric_name for m in metrics}
        assert "trimp" in names
        assert "hrss" in names
        assert "efficiency_factor" in names
        assert "aerobic_decoupling" in names

    def test_hr_zones(self, ext, activity_raw):
        metrics = ext.extract_activity_metrics(activity_raw)
        names = {m.metric_name for m in metrics}
        assert "hr_zone_1_sec" in names
        assert "hr_zones_detail" in names

    def test_metric_values(self, ext, activity_raw):
        metrics = ext.extract_activity_metrics(activity_raw)
        by_name = {m.metric_name: m for m in metrics}
        assert by_name["trimp"].numeric_value == 85
        assert by_name["efficiency_factor"].numeric_value == 1.67


class TestIntervalsWellness:
    def test_wellness_core(self, ext, wellness_raw):
        core = ext.extract_wellness_core("2025-03-25", wellness=wellness_raw)
        assert core["sleep_score"] == 80
        assert core["resting_hr"] == 52
        assert core["weight_kg"] == 70.5

    def test_fitness(self, ext, wellness_raw):
        fit = ext.extract_fitness("2025-03-25", wellness_raw)
        assert fit["source"] == "intervals"
        assert fit["ctl"] == 45.2
        assert fit["atl"] == 52.1
        assert fit["tsb"] == -6.9
