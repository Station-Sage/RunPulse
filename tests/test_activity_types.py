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

    def test_garmin_indoor_running(self):
        assert normalize_activity_type("indoor_running", "garmin") == "running"

    def test_indoor_running_case_whitespace(self):
        assert normalize_activity_type(" Indoor_Running ", "garmin") == "running"


class TestSportFamily:
    def test_boundary_types(self):
        from src.utils.activity_types import sport_family
        assert sport_family("race") == "running"
        assert sport_family("treadmill") == "running"
        assert sport_family("hiit") == "other"
        assert sport_family("HighIntensityIntervalTraining") == "other"
        assert sport_family("yoga") == "other"
        assert sport_family("") == "other"
        assert sport_family("Run", "strava") == "running"

    def test_family_raw_types_running(self):
        from src.utils.activity_types import family_raw_types
        raws = family_raw_types("running")
        for k in ("running", "trail_running", "race", "treadmill", "treadmill_running", "Run", "TrailRun"):
            assert k in raws
        for k in ("hiit", "swimming", "strength_training"):
            assert k not in raws

    def test_family_clause(self):
        from src.utils.activity_types import family_clause, family_raw_types
        sql, params = family_clause("running", "a.activity_type")
        assert sql.startswith("a.activity_type IN (") and "LIKE" not in sql
        assert tuple(sorted(params)) == family_raw_types("running")
        assert family_clause("nope") == ("0", [])

    def test_sport_labels_reexport(self):
        from src.services.activity_list_filters import SPORT_LABELS as A
        from src.utils.activity_types import SPORT_LABELS as B
        assert A is B
