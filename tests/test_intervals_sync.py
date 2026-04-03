"""DoD #9: Intervals.icu activity + wellness sync — mock 기반."""
import sqlite3
from unittest.mock import patch, MagicMock

from src.db_setup import create_tables
from src.sync.intervals_activity_sync import sync, sync_wellness


def _conn():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    return c


ICU_CONFIG = {
    "intervals": {"athlete_id": "i12345", "api_key": "test_key"}
}

SAMPLE_ICU_ACTIVITY = {
    "id": "i_a_001",
    "name": "Easy Run",
    "type": "Run",
    "start_date_local": "2026-04-01T07:00:00",
    "distance": 6000.0,
    "moving_time": 2100,
    "elapsed_time": 2200,
    "average_heartrate": 140,
    "max_heartrate": 162,
    "average_speed": 2.86,
    "max_speed": 4.0,
    "total_elevation_gain": 45.0,
    "calories": 380,
    "icu_training_load": 78,
    "icu_ftp": 260,
}

# extractor가 기대하는 필드명으로 맞춤
SAMPLE_ICU_WELLNESS = {
    "id": "2026-04-01",
    "ctl": 55.0,
    "atl": 48.0,
    "restingHR": 52,
    "hrv": 45.0,
    "sleepSecs": 28800,
    "sleepQuality": 80,
    "weight": 70.5,
    "steps": 9200,
}


class TestIntervalsActivitySync:
    @patch("src.sync.intervals_activity_sync.requests")
    def test_sync_one_activity(self, mock_requests):
        conn = _conn()
        resp = MagicMock()
        resp.json.return_value = [SAMPLE_ICU_ACTIVITY]
        resp.raise_for_status = MagicMock()
        mock_requests.get.return_value = resp

        result = sync(conn, days=7, config=ICU_CONFIG, _sleep_fn=lambda _: None)

        assert result.source == "intervals"
        assert result.synced_count == 1

        row = conn.execute("SELECT source, source_id FROM activity_summaries").fetchone()
        assert row[0] == "intervals"
        assert row[1] == "i_a_001"

    @patch("src.sync.intervals_activity_sync.requests")
    def test_sync_empty(self, mock_requests):
        conn = _conn()
        resp = MagicMock()
        resp.json.return_value = []
        resp.raise_for_status = MagicMock()
        mock_requests.get.return_value = resp

        result = sync(conn, days=7, config=ICU_CONFIG, _sleep_fn=lambda _: None)
        assert result.total_items == 0

    @patch("src.sync.intervals_activity_sync.requests")
    def test_sync_skip_unchanged(self, mock_requests):
        conn = _conn()
        resp = MagicMock()
        resp.json.return_value = [SAMPLE_ICU_ACTIVITY]
        resp.raise_for_status = MagicMock()
        mock_requests.get.return_value = resp

        sync(conn, days=7, config=ICU_CONFIG, _sleep_fn=lambda _: None)
        r2 = sync(conn, days=7, config=ICU_CONFIG, _sleep_fn=lambda _: None)
        assert r2.skipped_count == 1

    def test_sync_no_credentials(self):
        conn = _conn()
        result = sync(conn, days=7, config={"intervals": {}}, _sleep_fn=lambda _: None)
        assert result.status == "skipped"


class TestIntervalsWellnessSync:
    @patch("src.sync.intervals_activity_sync.requests")
    def test_wellness_sync(self, mock_requests):
        conn = _conn()
        resp = MagicMock()
        resp.json.return_value = [SAMPLE_ICU_WELLNESS]
        resp.raise_for_status = MagicMock()
        mock_requests.get.return_value = resp

        result = sync_wellness(conn, days=7, config=ICU_CONFIG, _sleep_fn=lambda _: None)

        assert result.source == "intervals"
        assert result.job_type == "wellness"
        assert result.synced_count == 1

        row = conn.execute(
            "SELECT sleep_score, hrv_last_night, resting_hr, steps FROM daily_wellness"
        ).fetchone()
        assert row is not None
        assert row[0] == 80    # sleepQuality → sleep_score
        assert row[1] == 45.0  # hrv → hrv_last_night
        assert row[2] == 52    # restingHR → resting_hr
        assert row[3] == 9200  # steps

    @patch("src.sync.intervals_activity_sync.requests")
    def test_wellness_skip_unchanged(self, mock_requests):
        conn = _conn()
        resp = MagicMock()
        resp.json.return_value = [SAMPLE_ICU_WELLNESS]
        resp.raise_for_status = MagicMock()
        mock_requests.get.return_value = resp

        sync_wellness(conn, days=7, config=ICU_CONFIG, _sleep_fn=lambda _: None)
        r2 = sync_wellness(conn, days=7, config=ICU_CONFIG, _sleep_fn=lambda _: None)
        assert r2.skipped_count == 1

    @patch("src.sync.intervals_activity_sync.requests")
    def test_wellness_fitness_stored(self, mock_requests):
        """ctl/atl/vo2max → daily_fitness 저장."""
        conn = _conn()
        resp = MagicMock()
        resp.json.return_value = [SAMPLE_ICU_WELLNESS]
        resp.raise_for_status = MagicMock()
        mock_requests.get.return_value = resp

        sync_wellness(conn, days=7, config=ICU_CONFIG, _sleep_fn=lambda _: None)

        row = conn.execute("SELECT ctl, atl FROM daily_fitness WHERE source='intervals'").fetchone()
        assert row is not None
        assert row[0] == 55.0
        assert row[1] == 48.0
