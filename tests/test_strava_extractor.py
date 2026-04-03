"""Strava Extractor 단위 테스트."""

import json
import pytest
from pathlib import Path
from src.sync.extractors.strava_extractor import StravaExtractor


FIXTURES = Path(__file__).parent / "fixtures" / "api" / "strava"


@pytest.fixture
def ext():
    return StravaExtractor()


@pytest.fixture
def activity_raw():
    with open(FIXTURES / "activity_minimal.json") as f:
        return json.load(f)


class TestStravaActivityCore:
    def test_required_fields(self, ext, activity_raw):
        core = ext.extract_activity_core(activity_raw)
        assert core["source"] == "strava"
        assert core["source_id"] == "9876543210"
        assert core["activity_type"] == "running"
        assert core["start_time"] == "2025-03-25T09:30:00Z"

    def test_distance_time(self, ext, activity_raw):
        core = ext.extract_activity_core(activity_raw)
        assert core["distance_m"] == 10050.0
        assert core["duration_sec"] == 3150
        assert core["moving_time_sec"] == 3060

    def test_suffer_score(self, ext, activity_raw):
        core = ext.extract_activity_core(activity_raw)
        assert core["suffer_score"] == 78

    def test_latlng(self, ext, activity_raw):
        core = ext.extract_activity_core(activity_raw)
        assert abs(core["start_lat"] - 37.5665) < 0.001

    def test_source_url(self, ext, activity_raw):
        core = ext.extract_activity_core(activity_raw)
        assert "9876543210" in core["source_url"]

    def test_no_none_values(self, ext, activity_raw):
        core = ext.extract_activity_core(activity_raw)
        for v in core.values():
            assert v is not None


class TestStravaActivityMetrics:
    def test_basic_metrics(self, ext, activity_raw):
        metrics = ext.extract_activity_metrics(activity_raw)
        names = {m.metric_name for m in metrics}
        assert "kilojoules" in names
        assert "perceived_exertion" in names
        assert "kudos_count" in names

    def test_splits_as_json(self, ext, activity_raw):
        metrics = ext.extract_activity_metrics(activity_raw)
        splits = [m for m in metrics if m.metric_name == "splits_metric"]
        assert len(splits) == 1
        assert splits[0].json_value is not None


class TestStravaBestEfforts:
    def test_extraction(self, ext, activity_raw):
        efforts = ext.extract_best_efforts(activity_raw)
        assert len(efforts) == 1
        assert efforts[0]["effort_name"] == "1k"
        assert efforts[0]["elapsed_sec"] == 280


class TestStravaStreams:
    def test_stream_extraction(self, ext):
        streams = [
            {"type": "time", "data": [0, 1, 2, 3]},
            {"type": "heartrate", "data": [120, 130, 140, 150]},
            {"type": "distance", "data": [0, 3.2, 6.4, 9.6]},
            {"type": "latlng", "data": [[37.5, 126.9], [37.51, 126.91], [37.52, 126.92], [37.53, 126.93]]},
        ]
        rows = ext.extract_activity_streams(streams)
        assert len(rows) == 4
        assert rows[0]["elapsed_sec"] == 0
        assert rows[0]["heart_rate"] == 120
        assert abs(rows[0]["latitude"] - 37.5) < 0.01

    def test_empty_streams(self, ext):
        assert ext.extract_activity_streams([]) == []
        assert ext.extract_activity_streams({}) == []
