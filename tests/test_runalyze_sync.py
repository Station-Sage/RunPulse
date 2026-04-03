"""DoD #10: Runalyze basic sync — mock 기반."""
import sqlite3
from unittest.mock import patch, MagicMock

from src.db_setup import create_tables
from src.sync.runalyze_activity_sync import sync


def _conn():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    return c


RUNALYZE_CONFIG = {"runalyze": {"token": "test_token"}}

SAMPLE_RUNALYZE_ACTIVITY = {
    "id": "r_001",
    "title": "Evening Run",
    "sport": "running",
    "datetime": "2026-04-01T19:00:00+09:00",
    "distance": 7200.0,
    "s": 2400,
    "elapsed_time": 2500,
    "heart_rate_avg": 148,
    "heart_rate_max": 170,
    "cadence": 176,
    "power": 235,
    "elevation": 60,
    "calories": 450,
    "vo2max": 50.5,
    "vdot": 48.2,
    "trimp": 120,
}


class TestRunalyzeSync:
    @patch("src.sync.runalyze_activity_sync.requests")
    def test_sync_one_activity(self, mock_requests):
        conn = _conn()
        resp = MagicMock()
        resp.json.return_value = [SAMPLE_RUNALYZE_ACTIVITY]
        resp.raise_for_status = MagicMock()
        mock_requests.get.return_value = resp

        result = sync(conn, days=7, config=RUNALYZE_CONFIG, _sleep_fn=lambda _: None)

        assert result.source == "runalyze"
        assert result.synced_count == 1

        row = conn.execute("SELECT source, source_id FROM activity_summaries").fetchone()
        assert row[0] == "runalyze"
        assert row[1] == "r_001"

    @patch("src.sync.runalyze_activity_sync.requests")
    def test_sync_empty(self, mock_requests):
        conn = _conn()
        resp = MagicMock()
        resp.json.return_value = []
        resp.raise_for_status = MagicMock()
        mock_requests.get.return_value = resp

        result = sync(conn, days=7, config=RUNALYZE_CONFIG, _sleep_fn=lambda _: None)
        assert result.total_items == 0

    @patch("src.sync.runalyze_activity_sync.requests")
    def test_sync_skip_unchanged(self, mock_requests):
        conn = _conn()
        resp = MagicMock()
        resp.json.return_value = [SAMPLE_RUNALYZE_ACTIVITY]
        resp.raise_for_status = MagicMock()
        mock_requests.get.return_value = resp

        sync(conn, days=7, config=RUNALYZE_CONFIG, _sleep_fn=lambda _: None)
        r2 = sync(conn, days=7, config=RUNALYZE_CONFIG, _sleep_fn=lambda _: None)
        assert r2.skipped_count == 1

    def test_sync_no_token(self):
        conn = _conn()
        result = sync(conn, days=7, config={"runalyze": {}}, _sleep_fn=lambda _: None)
        assert result.status == "skipped"

    @patch("src.sync.runalyze_activity_sync.requests")
    def test_sync_dict_response(self, mock_requests):
        """Runalyze가 {data: [...]} 형태로 응답하는 경우."""
        conn = _conn()
        resp = MagicMock()
        resp.json.return_value = {"data": [SAMPLE_RUNALYZE_ACTIVITY]}
        resp.raise_for_status = MagicMock()
        mock_requests.get.return_value = resp

        result = sync(conn, days=7, config=RUNALYZE_CONFIG, _sleep_fn=lambda _: None)
        assert result.synced_count == 1

    @patch("src.sync.runalyze_activity_sync.requests")
    def test_metrics_stored(self, mock_requests):
        conn = _conn()
        resp = MagicMock()
        resp.json.return_value = [SAMPLE_RUNALYZE_ACTIVITY]
        resp.raise_for_status = MagicMock()
        mock_requests.get.return_value = resp

        sync(conn, days=7, config=RUNALYZE_CONFIG, _sleep_fn=lambda _: None)

        count = conn.execute("SELECT COUNT(*) FROM metric_store").fetchone()[0]
        assert count > 0
