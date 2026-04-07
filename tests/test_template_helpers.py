"""tests/test_template_helpers.py — Phase 5-E 헬퍼 함수 테스트."""
import pytest

from src.web.template_helpers import (
    confidence_badge,
    format_distance,
    format_duration,
    format_metric,
    format_pace,
    format_speed,
    format_time_prediction,
    interpret_metric_level,
    metric_display_name,
    metric_level_color,
    metric_unit,
    provider_badge,
)


# format_distance

def test_format_distance_km():
    assert format_distance(10020.0) == "10.02km"


def test_format_distance_decimals():
    assert format_distance(10000.0, decimals=1) == "10.0km"


def test_format_distance_zero():
    assert format_distance(0) == "0.00km"


def test_format_distance_none():
    assert format_distance(None) == ""


# format_pace

def test_format_pace_normal():
    assert format_pace(312.5) == "5:12"


def test_format_pace_exact():
    assert format_pace(300.0) == "5:00"


def test_format_pace_zero():
    assert format_pace(0) == ""


def test_format_pace_none():
    assert format_pace(None) == ""


# format_duration

def test_format_duration_under_hour():
    assert format_duration(735) == "12:15"


def test_format_duration_over_hour():
    assert format_duration(3735) == "1:02:15"


def test_format_duration_zero():
    assert format_duration(0) == "0:00"


def test_format_duration_none():
    assert format_duration(None) == ""


# format_speed

def test_format_speed():
    result = format_speed(3.2)
    assert "km/h" in result
    assert "11.5" in result


def test_format_speed_none():
    assert format_speed(None) == ""


# format_time_prediction

def test_format_time_prediction():
    assert format_time_prediction(6135) == "1:42:15"


def test_format_time_prediction_none():
    assert format_time_prediction(None) == ""


# interpret_metric_level

def test_interpret_utrs_good():
    assert interpret_metric_level("utrs", 72.3) == "양호"


def test_interpret_utrs_great():
    assert interpret_metric_level("utrs", 86.0) == "우수"


def test_interpret_cirs_low():
    assert interpret_metric_level("cirs", 28.1) == "낮음"


def test_interpret_unknown_metric():
    assert interpret_metric_level("unknown_metric_xyz", 50.0) == ""


def test_interpret_none_value():
    assert interpret_metric_level("utrs", None) == ""


# metric_level_color

def test_metric_level_color_green():
    assert metric_level_color("utrs", 86.0) == "green"  # 우수


def test_metric_level_color_yellow():
    # utrs 보통 구간 (50~70)
    assert metric_level_color("utrs", 60.0) == "yellow"


def test_metric_level_color_low_higher_is_better():
    # utrs 낮음(30~50), HIGHER_IS_BETTER=True → red
    assert metric_level_color("utrs", 40.0) == "red"


def test_metric_level_color_low_lower_is_better():
    # aerobic_decoupling_rp 낮음(0~5=우수), HIGHER_IS_BETTER=False
    assert metric_level_color("aerobic_decoupling_rp", 3.0) == "green"


# confidence_badge

def test_confidence_badge_high():
    assert confidence_badge(0.9) == "높음"


def test_confidence_badge_medium():
    assert confidence_badge(0.6) == "보통"


def test_confidence_badge_low():
    assert confidence_badge(0.3) == "낮음"


def test_confidence_badge_none():
    assert confidence_badge(None) == ""


# provider_badge

def test_provider_badge_runpulse():
    assert provider_badge("runpulse:formula_v1") == "RunPulse"


def test_provider_badge_garmin():
    assert provider_badge("garmin") == "Garmin"


def test_provider_badge_unknown():
    assert provider_badge("my_custom_provider") == "my_custom_provider"


def test_provider_badge_none():
    assert provider_badge(None) == ""


# metric_display_name / metric_unit

def test_metric_display_name_known():
    name = metric_display_name("trimp")
    assert isinstance(name, str)
    assert len(name) > 0


def test_metric_display_name_unknown():
    assert metric_display_name("nonexistent_xyz") == "nonexistent_xyz"


def test_metric_unit_known():
    # trimp 단위 확인 (registry에서 조회)
    unit = metric_unit("trimp")
    assert isinstance(unit, str)


def test_metric_unit_unknown():
    assert metric_unit("nonexistent_xyz") == ""
