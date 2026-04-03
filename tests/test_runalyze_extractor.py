"""Runalyze Extractor 단위 테스트."""

import json
import pytest
from pathlib import Path
from src.sync.extractors.runalyze_extractor import RunalyzeExtractor


FIXTURES = Path(__file__).parent / "fixtures" / "api" / "runalyze"


@pytest.fixture
def ext():
    return RunalyzeExtractor()


@pytest.fixture
def activity_raw():
    with open(FIXTURES / "activity_minimal.json") as f:
        return json.load(f)


class TestRunalyzeActivityCore:
    def test_required_fields(self, ext, activity_raw):
        core = ext.extract_activity_core(activity_raw)
        assert core["source"] == "runalyze"
        assert core["source_id"] == "7890"
        assert core["activity_type"] == "running"

    def test_distance_time(self, ext, activity_raw):
        core = ext.extract_activity_core(activity_raw)
        assert core["distance_m"] == 10025.0
        assert core["duration_sec"] == 3115

    def test_pace_calculated(self, ext, activity_raw):
        core = ext.extract_activity_core(activity_raw)
        expected = round(3115 / (10025 / 1000), 2)
        assert core["avg_pace_sec_km"] == expected


class TestRunalyzeActivityMetrics:
    def test_fitness_metrics(self, ext, activity_raw):
        metrics = ext.extract_activity_metrics(activity_raw)
        names = {m.metric_name for m in metrics}
        assert "effective_vo2max" in names
        assert "vdot" in names
        assert "marathon_shape" in names

    def test_race_predictions(self, ext, activity_raw):
        metrics = ext.extract_activity_metrics(activity_raw)
        by_name = {m.metric_name: m for m in metrics}
        assert by_name["race_pred_5k_sec"].numeric_value == 1190
        assert by_name["race_pred_marathon_sec"].numeric_value == 11300

    def test_trimp(self, ext, activity_raw):
        metrics = ext.extract_activity_metrics(activity_raw)
        by_name = {m.metric_name: m for m in metrics}
        assert by_name["trimp"].numeric_value == 83
