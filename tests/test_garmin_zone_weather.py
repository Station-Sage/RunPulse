"""garmin_zone_weather 단위 변환·None 처리 테스트."""

from src.sync.extractors.garmin_zone_weather import (
    f_to_c, hr_zone_seconds, mph_to_ms, weather_values,
)


def test_f_to_c():
    assert f_to_c(212) == 100.0
    assert f_to_c(None) is None


def test_mph_to_ms():
    assert round(mph_to_ms(10), 2) == 4.47
    assert mph_to_ms(None) is None


def test_hr_zone_seconds_real_list():
    zones = [{"zoneNumber": 1, "secsInZone": 60.0, "zoneLowBoundary": 90},
             {"zoneNumber": 2, "secsInZone": 120.0, "zoneLowBoundary": 110}]
    assert hr_zone_seconds(zones) == [60.0, 120.0, None, None, None]


def test_hr_zone_seconds_invalid():
    assert hr_zone_seconds(None) == [None] * 5
    assert hr_zone_seconds([]) == [None] * 5


def test_weather_values_converts_units():
    v = weather_values({"temp": 50, "dewPoint": 32, "relativeHumidity": 60,
                        "windSpeed": 10, "windDirection": 180})
    assert v["weather_temp_c"] == 10.0 and v["weather_dew_point_c"] == 0.0
    assert v["weather_wind_speed_ms"] == 4.47 and v["weather_humidity_pct"] == 60


def test_weather_values_indoor_empty():
    assert weather_values({"temp": None, "windSpeed": None}) == {}
    assert weather_values(None) == {}
