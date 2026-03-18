"""pace 유틸리티 테스트."""

import pytest

from src.utils.pace import (
    seconds_to_pace,
    pace_to_seconds,
    kmh_to_pace,
    pace_to_kmh,
    format_duration,
)


class TestSecondsToPace:
    def test_even_minutes(self):
        assert seconds_to_pace(300) == "5:00"

    def test_with_seconds(self):
        assert seconds_to_pace(330) == "5:30"

    def test_single_digit_seconds(self):
        assert seconds_to_pace(305) == "5:05"

    def test_fast_pace(self):
        assert seconds_to_pace(210) == "3:30"


class TestPaceToSeconds:
    def test_even_minutes(self):
        assert pace_to_seconds("5:00") == 300

    def test_with_seconds(self):
        assert pace_to_seconds("4:30") == 270

    def test_roundtrip(self):
        assert pace_to_seconds(seconds_to_pace(315)) == 315


class TestKmhToPace:
    def test_12kmh(self):
        assert kmh_to_pace(12.0) == 300

    def test_10kmh(self):
        assert kmh_to_pace(10.0) == 360

    def test_zero_raises(self):
        with pytest.raises(ValueError):
            kmh_to_pace(0)


class TestPaceToKmh:
    def test_300sec(self):
        assert pace_to_kmh(300) == 12.0

    def test_360sec(self):
        assert pace_to_kmh(360) == 10.0

    def test_zero_raises(self):
        with pytest.raises(ValueError):
            pace_to_kmh(0)


class TestFormatDuration:
    def test_under_hour(self):
        assert format_duration(1800) == "30:00"

    def test_over_hour(self):
        assert format_duration(3661) == "1:01:01"

    def test_zero(self):
        assert format_duration(0) == "0:00"

    def test_exact_hour(self):
        assert format_duration(3600) == "1:00:00"
