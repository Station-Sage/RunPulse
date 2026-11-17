"""garmin_activity_extras — 부가 엔드포인트 조회·저장·재조립."""
import dataclasses
import sqlite3
from unittest.mock import MagicMock

import pytest

from src.db_setup import create_tables
from src.sync.garmin_activity_extras import (
    RateLimitStop, fetch_activity_extras, load_activity_extras,
)
from src.sync.rate_limiter import RateLimiter
from src.sync.sync_result import SyncResult

ZONES = [{"zoneNumber": 1, "secsInZone": 10.0, "zoneLowBoundary": 100}]
WEATHER = {"temp": 60, "windSpeed": 5}


def _setup():
    conn = sqlite3.connect(":memory:")
    create_tables(conn)
    api = MagicMock()
    api.get_activity_hr_in_timezones.return_value = ZONES
    api.get_activity_weather.return_value = WEATHER
    limiter = RateLimiter("garmin", sleep_fn=lambda _: None)
    return conn, api, limiter, SyncResult(source="garmin", job_type="activity")


def test_fetch_stores_and_returns_both():
    conn, api, limiter, result = _setup()
    out = fetch_activity_extras(conn, api, limiter, result, "1", None)
    assert out == {"hrTimeInZones": ZONES, "activityWeather": WEATHER}
    assert result.api_calls == 2


def test_failure_continues_with_other_endpoint():
    conn, api, limiter, result = _setup()
    api.get_activity_hr_in_timezones.side_effect = RuntimeError("boom")
    out = fetch_activity_extras(conn, api, limiter, result, "1", None)
    assert out == {"activityWeather": WEATHER}


def test_rate_limit_raises_stop():
    conn, api, limiter, result = _setup()
    api.get_activity_hr_in_timezones.side_effect = RuntimeError("429 Too Many Requests")
    limiter.policy = dataclasses.replace(limiter.policy, max_retries=0)
    with pytest.raises(RateLimitStop):
        fetch_activity_extras(conn, api, limiter, result, "1", None)


def test_load_roundtrip_unwraps_list_payload():
    conn, api, limiter, result = _setup()
    fetch_activity_extras(conn, api, limiter, result, "1", None)
    assert load_activity_extras(conn, "1") == {"hrTimeInZones": ZONES, "activityWeather": WEATHER}


def test_load_missing_returns_empty():
    conn, *_ = _setup()
    assert load_activity_extras(conn, "999") == {}
