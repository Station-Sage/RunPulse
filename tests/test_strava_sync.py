"""DoD #8: Strava sync — OAuth + detail + streams mock 기반."""
import sqlite3
from unittest.mock import patch, MagicMock

from src.db_setup import create_tables
from src.sync.strava_activity_sync import sync


def _conn():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    return c


SAMPLE_STRAVA_ACTIVITY = {
    "id": 98765,
    "name": "Afternoon Run",
    "type": "Run",
    "sport_type": "Run",
    "start_date": "2026-04-01T14:00:00Z",
    "start_date_local": "2026-04-01T23:00:00",
    "distance": 8500.0,
    "moving_time": 2700,
    "elapsed_time": 2800,
    "average_speed": 3.15,
    "max_speed": 4.8,
    "average_heartrate": 155,
    "max_heartrate": 178,
    "average_cadence": 88,
    "total_elevation_gain": 85.0,
    "calories": 520,
    "suffer_score": 95,
}

SAMPLE_STRAVA_DETAIL = {
    **SAMPLE_STRAVA_ACTIVITY,
    "description": "Good run",
    "gear": {"id": "g123", "name": "Nike Pegasus"},
    "device_name": "Garmin Forerunner",
    "best_efforts": [
        {"name": "1k", "elapsed_time": 245, "distance": 1000, "pr_rank": 1},
        {"name": "5k", "elapsed_time": 1300, "distance": 5000, "pr_rank": None},
    ],
}

STRAVA_CONFIG = {
    "strava": {
        "client_id": "test",
        "client_secret": "secret",
        "refresh_token": "rt",
        "access_token": "at_valid",
        "expires_at": 9999999999,
    }
}


class TestStravaActivitySync:
    @patch("src.sync.strava_activity_sync.requests")
    def test_sync_one_activity(self, mock_requests):
        """Strava 활동 1개 sync."""
        conn = _conn()

        list_resp = MagicMock()
        list_resp.json.return_value = [SAMPLE_STRAVA_ACTIVITY]
        list_resp.raise_for_status = MagicMock()

        detail_resp = MagicMock()
        detail_resp.json.return_value = SAMPLE_STRAVA_DETAIL
        detail_resp.raise_for_status = MagicMock()

        mock_requests.get.side_effect = [list_resp, detail_resp]

        result = sync(conn, days=7, config=STRAVA_CONFIG, _sleep_fn=lambda _: None)

        assert result.source == "strava"
        assert result.synced_count == 1
        assert result.api_calls >= 2

        row = conn.execute("SELECT source, source_id, distance_m FROM activity_summaries").fetchone()
        assert row[0] == "strava"
        assert row[1] == "98765"

    @patch("src.sync.strava_activity_sync.requests")
    def test_sync_with_best_efforts(self, mock_requests):
        """best_efforts 저장 확인."""
        conn = _conn()

        list_resp = MagicMock()
        list_resp.json.return_value = [SAMPLE_STRAVA_ACTIVITY]
        list_resp.raise_for_status = MagicMock()

        detail_resp = MagicMock()
        detail_resp.json.return_value = SAMPLE_STRAVA_DETAIL
        detail_resp.raise_for_status = MagicMock()

        mock_requests.get.side_effect = [list_resp, detail_resp]

        sync(conn, days=7, config=STRAVA_CONFIG, include_streams=False, _sleep_fn=lambda _: None)

        efforts = conn.execute("SELECT COUNT(*) FROM activity_best_efforts").fetchone()[0]
        assert efforts >= 1

    @patch("src.sync.strava_activity_sync.requests")
    def test_sync_empty_list(self, mock_requests):
        """활동 없으면 성공."""
        conn = _conn()
        resp = MagicMock()
        resp.json.return_value = []
        resp.raise_for_status = MagicMock()
        mock_requests.get.return_value = resp

        result = sync(conn, days=7, config=STRAVA_CONFIG, _sleep_fn=lambda _: None)
        assert result.status == "success"
        assert result.total_items == 0

    @patch("src.sync.strava_activity_sync.requests")
    def test_sync_skip_unchanged(self, mock_requests):
        """동일 활동 재sync → skip."""
        conn = _conn()

        list_resp = MagicMock()
        list_resp.json.return_value = [SAMPLE_STRAVA_ACTIVITY]
        list_resp.raise_for_status = MagicMock()

        detail_resp = MagicMock()
        detail_resp.json.return_value = SAMPLE_STRAVA_DETAIL
        detail_resp.raise_for_status = MagicMock()

        mock_requests.get.side_effect = [list_resp, detail_resp]
        sync(conn, days=7, config=STRAVA_CONFIG, _sleep_fn=lambda _: None)

        mock_requests.get.side_effect = [list_resp]
        r2 = sync(conn, days=7, config=STRAVA_CONFIG, _sleep_fn=lambda _: None)
        assert r2.skipped_count == 1

    def test_sync_no_token(self):
        """토큰 없으면 failed."""
        conn = _conn()
        result = sync(conn, days=7, config={"strava": {}}, _sleep_fn=lambda _: None)
        assert result.status == "failed"
