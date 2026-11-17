"""A7: Intervals wellness 확장 지표, Intervals/Strava Lap·존 수집 테스트."""
import sqlite3
from unittest.mock import MagicMock, patch

import pytest
import requests

from src.db_setup import create_tables
from src.sync.extractors.intervals_extractor import IntervalsExtractor
from src.sync.extractors.strava_extractor import StravaExtractor
from src.sync.intervals_laps_sync import fetch_and_save_interval_laps
from src.sync.strava_laps_zones_sync import fetch_and_save_laps_zones
from src.sync.sync_result import SyncResult


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    c.execute(
        "INSERT INTO activity_summaries (source, source_id, activity_type, start_time) "
        "VALUES ('intervals', 'i1', 'running', '2026-04-01T07:00:00')"
    )
    c.commit()
    return c


def _limiter():
    return MagicMock()


def _resp(payload, status=200):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = payload
    if status >= 400:
        err = requests.HTTPError(f"{status}")
        err.response = r
        r.raise_for_status.side_effect = err
    return r


ICU = {"icu_intervals": [
    {"type": "WARMUP", "elapsed_time": 600, "moving_time": 598, "distance": 1500.0,
     "average_speed": 2.5, "average_heartrate": 130.4, "max_heartrate": 140, "average_cadence": 82},
    {"type": "WORK", "elapsed_time": 300, "moving_time": 300, "distance": 1000.0, "average_speed": 3.333},
    {"type": "RECOVERY", "elapsed_time": 120, "distance": 200.0},
    "garbage",
]}


class TestIntervalsWellnessMetrics:
    def test_extra_keys(self):
        recs = IntervalsExtractor().extract_wellness_metrics(
            "2026-04-01", wellness={"hrvSDNN": 55.0, "avgSleepingHR": 48.5, "sleepQuality": 2})
        by = {r.metric_name: r for r in recs}
        assert by["icu_hrv_sdnn"].numeric_value == 55.0
        assert by["icu_sleeping_hr_avg"].numeric_value == 48.5
        assert by["icu_sleep_quality"].numeric_value == 2

    def test_empty(self):
        assert IntervalsExtractor().extract_wellness_metrics("2026-04-01", wellness={}) == []


class TestIntervalsLaps:
    def test_extract_kind_mapping(self):
        laps = IntervalsExtractor().extract_activity_laps(ICU)
        assert [l["lap_kind"] for l in laps] == ["WARMUP", "ACTIVE", "RECOVERY"]
        assert laps[0]["avg_pace_sec_km"] == 400.0
        assert laps[0]["avg_hr"] == 130

    def test_extract_invalid(self):
        assert IntervalsExtractor().extract_activity_laps({}) == []

    def test_fetch_saves(self, conn):
        aid = conn.execute("SELECT id FROM activity_summaries").fetchone()[0]
        res = SyncResult(source="intervals", job_type="activity")
        with patch("src.sync.intervals_laps_sync.requests.get", return_value=_resp(ICU)):
            n = fetch_and_save_interval_laps(
                conn, IntervalsExtractor(), _limiter(), res, "http://x", ("a", "b"),
                {"id": "i1", "type": "Run"}, aid)
        assert n == 3
        assert conn.execute("SELECT COUNT(*) FROM activity_laps WHERE activity_id=?", (aid,)).fetchone()[0] == 3

    def test_non_run_skipped(self, conn):
        with patch("src.sync.intervals_laps_sync.requests.get") as g:
            n = fetch_and_save_interval_laps(
                conn, IntervalsExtractor(), _limiter(), SyncResult(source="intervals", job_type="activity"),
                "http://x", None, {"id": "i1", "type": "Ride"}, 1)
        assert n == 0
        g.assert_not_called()

    def test_request_failure_is_nonfatal(self, conn):
        with patch("src.sync.intervals_laps_sync.requests.get", side_effect=requests.ConnectionError("x")):
            n = fetch_and_save_interval_laps(
                conn, IntervalsExtractor(), _limiter(), SyncResult(source="intervals", job_type="activity"),
                "http://x", None, {"id": "i1", "type": "Run"}, 1)
        assert n == 0


STRAVA_LAPS = [
    {"lap_index": 1, "start_date_local": "2026-04-01T07:00:00Z", "elapsed_time": 300, "moving_time": 298,
     "distance": 1000.0, "average_speed": 3.333, "average_heartrate": 150.2, "max_heartrate": 160,
     "average_cadence": 85.0, "total_elevation_gain": 4.0},
    {"lap_index": 2, "elapsed_time": 310, "moving_time": 310, "distance": 1000.0, "average_speed": 3.2},
]
STRAVA_ZONES = [
    {"type": "heartrate", "distribution_buckets": [
        {"min": 0, "max": 120, "time": 60}, {"min": 120, "max": 140, "time": 120},
        {"min": 140, "max": 160, "time": 300}, {"min": 160, "max": 180, "time": 30},
        {"min": 180, "max": -1, "time": 0}]},
    {"type": "power", "distribution_buckets": [{"min": 0, "max": 100, "time": 5}]},
]


class TestStravaLapsZones:
    def test_extract_laps(self):
        laps = StravaExtractor().extract_activity_laps(STRAVA_LAPS)
        assert len(laps) == 2
        assert laps[0]["distance_m"] == 1000.0
        assert laps[0]["avg_hr"] == 150
        assert laps[0]["avg_pace_sec_km"] == pytest.approx(300.0, abs=0.1)

    def test_extract_zones(self):
        by = {r.metric_name: r for r in StravaExtractor().extract_zone_metrics(STRAVA_ZONES)}
        assert by["hr_zone_3_sec"].numeric_value == 300
        assert "hr_zones_detail" in by
        assert "hr_zone_6_sec" not in by

    def test_extract_zones_invalid(self):
        assert StravaExtractor().extract_zone_metrics({"x": 1}) == []
        assert StravaExtractor().extract_zone_metrics([{"type": "power"}]) == []

    def test_fetch_saves_laps_and_zones(self, conn):
        aid = conn.execute("SELECT id FROM activity_summaries").fetchone()[0]
        res = SyncResult(source="strava", job_type="activity")
        responses = {"laps": _resp(STRAVA_LAPS), "zones": _resp(STRAVA_ZONES)}
        with patch("src.sync.strava_laps_zones_sync.requests.get",
                   side_effect=lambda url, **kw: responses[url.rsplit("/", 1)[1]]):
            fetch_and_save_laps_zones(conn, {}, StravaExtractor(), _limiter(), res, "s1", aid)
        assert conn.execute("SELECT COUNT(*) FROM activity_laps WHERE activity_id=?", (aid,)).fetchone()[0] == 2
        assert conn.execute(
            "SELECT COUNT(*) FROM metric_store WHERE scope_type='activity' AND metric_name='hr_zone_3_sec'"
        ).fetchone()[0] == 1

    def test_zones_403_skipped(self, conn):
        aid = conn.execute("SELECT id FROM activity_summaries").fetchone()[0]
        res = SyncResult(source="strava", job_type="activity")
        responses = {"laps": _resp(STRAVA_LAPS), "zones": _resp({}, 403)}
        with patch("src.sync.strava_laps_zones_sync.requests.get",
                   side_effect=lambda url, **kw: responses[url.rsplit("/", 1)[1]]):
            fetch_and_save_laps_zones(conn, {}, StravaExtractor(), _limiter(), res, "s1", aid)
        assert conn.execute("SELECT COUNT(*) FROM activity_laps WHERE activity_id=?", (aid,)).fetchone()[0] == 2

    def test_429_reraised(self, conn):
        res = SyncResult(source="strava", job_type="activity")
        with patch("src.sync.strava_laps_zones_sync.requests.get", return_value=_resp({}, 429)):
            with pytest.raises(requests.HTTPError):
                fetch_and_save_laps_zones(conn, {}, StravaExtractor(), _limiter(), res, "s1", 1)
