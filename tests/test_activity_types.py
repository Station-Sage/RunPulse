"""activity_types.py 단위 테스트."""

import pytest
from src.utils.activity_types import normalize_activity_type


class TestNormalizeActivityType:
    def test_garmin_running(self):
        assert normalize_activity_type("running", "garmin") == "running"

    def test_garmin_trail(self):
        assert normalize_activity_type("trail_running", "garmin") == "running"

    def test_strava_run(self):
        assert normalize_activity_type("Run", "strava") == "running"

    def test_strava_trail_run(self):
        assert normalize_activity_type("TrailRun", "strava") == "running"

    def test_strava_ride(self):
        assert normalize_activity_type("Ride", "strava") == "cycling"

    def test_intervals_run(self):
        assert normalize_activity_type("Run", "intervals") == "running"

    def test_unknown_type_passthrough(self):
        assert normalize_activity_type("yoga", "garmin") == "yoga"

    def test_empty_string(self):
        assert normalize_activity_type("", "garmin") == "unknown"

    def test_case_insensitive(self):
        assert normalize_activity_type("RUNNING", "garmin") == "running"

    def test_cycling_variants(self):
        assert normalize_activity_type("cycling", None) == "cycling"
        assert normalize_activity_type("road_cycling", None) == "cycling"
