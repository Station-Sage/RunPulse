"""P7-PRED-86: Open-Meteo 단일 클라이언트(provider.py) — 요청 파라미터·보간·WBGT."""
from datetime import date

from src.weather import provider as om


def _hourly(day="2026-07-01"):
    hrs = [f"{day}T{h:02d}:00" for h in range(24)]
    return {"hourly": {"time": hrs, "temperature_2m": [20.0 + h * 0.5 for h in range(24)],
                       "relative_humidity_2m": [70] * 24, "dew_point_2m": [15.0] * 24,
                       "apparent_temperature": [22.0] * 24, "wind_speed_10m": [2.0] * 24,
                       "shortwave_radiation": [100.0] * 24}}


def test_request_params_archive_vs_forecast():
    url, p = om.request_params(37.51234, 126.9876, "2026-07-01", date(2026, 9, 26))
    assert url == om.ARCHIVE_URL and (p["latitude"], p["longitude"]) == (37.51, 126.99) and p["start_date"] == "2026-07-01"
    url, p = om.request_params(37.5, 127.0, "2026-09-24", date(2026, 9, 26))
    assert url == om.FORECAST_URL and p["past_days"] == 7


def test_at_time_interpolates_and_wbgt():
    rows = om.day_rows(_hourly()["hourly"], "2026-07-01")
    w = om.at_time(rows, 7.5)                    # 07:30 → 23.5 + 0.25 = 23.75
    assert w["temp_c"] == 23.75 and w["wbgt_c"] == 25.5
