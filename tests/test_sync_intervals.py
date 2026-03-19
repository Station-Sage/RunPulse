"""Intervals.icu sync 테스트."""

from datetime import datetime
from unittest.mock import patch

from src.sync.intervals import sync_activities, sync_wellness


class TestSyncActivities:
    @patch("src.sync.intervals.api.get")
    def test_inserts_activity(self, mock_get, db_conn, sample_config):
        now = datetime.now().isoformat()
        mock_get.return_value = [{
            "id": "i789",
            "start_date_local": now,
            "distance": 10000,
            "moving_time": 3000,
            "average_heartrate": 148,
            "max_heartrate": 172,
            "average_cadence": 180,
            "total_elevation_gain": 40,
            "calories": 460,
            "name": "Run",
            "type": "Run",
            "icu_training_load": 95,
            "icu_intensity": 0.75,
            "icu_hrss": 88,
        }]

        count = sync_activities(sample_config, db_conn, days=7)
        assert count == 1

        row = db_conn.execute("SELECT source, source_id FROM activities").fetchone()
        assert row[0] == "intervals"
        assert row[1] == "i789"

        metrics = db_conn.execute("SELECT metric_name FROM source_metrics ORDER BY metric_name").fetchall()
        names = [m[0] for m in metrics]
        assert "icu_training_load" in names


class TestSyncWellness:
    @patch("src.sync.intervals.api.get")
    def test_inserts_wellness(self, mock_get, db_conn, sample_config):
        mock_get.return_value = [{
            "id": "2026-03-18",
            "sleepQuality": 4,
            "sleepSecs": 28800,
            "hrv": 42,
            "restingHR": 50,
            "readiness": None,
            "ctl": 42.3,
            "atl": 55.1,
        }]

        count = sync_wellness(sample_config, db_conn, days=7)
        assert count == 1

        row = db_conn.execute("SELECT hrv_value, resting_hr FROM daily_wellness").fetchone()
        assert row[0] == 42
        assert row[1] == 50
