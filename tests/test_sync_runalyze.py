"""Runalyze sync 테스트."""

from datetime import datetime
from unittest.mock import patch

from src.sync.runalyze import sync_activities


class TestSyncActivities:
    @patch("src.sync.runalyze.api.get")
    def test_inserts_activity(self, mock_get, db_conn, sample_config):
        now = datetime.now().isoformat()
        mock_get.side_effect = [
            # 활동 목록
            [{
                "id": 999,
                "datetime": now,
                "distance": 10000,
                "s": 3000,
                "heart_rate_avg": 155,
                "heart_rate_max": 180,
                "elevation": 55,
                "calories": 510,
                "title": "Run",
            }],
            # 상세
            {
                "vo2max": 48.5,
                "vdot": 44.2,
                "trimp": 120,
            },
        ]

        count = sync_activities(sample_config, db_conn, days=7)
        assert count == 1

        row = db_conn.execute("SELECT source, source_id FROM activities").fetchone()
        assert row[0] == "runalyze"
        assert row[1] == "999"

        metrics = db_conn.execute("SELECT metric_name, metric_value FROM source_metrics ORDER BY metric_name").fetchall()
        metric_dict = {m[0]: m[1] for m in metrics}
        assert metric_dict["effective_vo2max"] == 48.5
        assert metric_dict["vdot"] == 44.2

    @patch("src.sync.runalyze.api.get")
    def test_skip_old_activity(self, mock_get, db_conn, sample_config):
        """days 범위 밖 활동은 건너뜀."""
        mock_get.return_value = [{
            "id": 888,
            "datetime": "2020-01-01T07:00:00",
            "distance": 10000,
            "s": 3000,
        }]

        count = sync_activities(sample_config, db_conn, days=7)
        assert count == 0
