"""Runalyze sync 테스트."""

import pytest
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
            # 상세 (marathon_shape, race_prediction 추가)
            {
                "vo2max": 48.5,
                "vdot": 44.2,
                "trimp": 120,
                "marathon_shape": 92.5,
                "race_prediction_5000": 1200,
                "race_prediction_10000": 2520,
            },
        ]

        count = sync_activities(sample_config, db_conn, days=7)
        assert count == 1

        row = db_conn.execute("SELECT source, source_id FROM activities").fetchone()
        assert row[0] == "runalyze"
        assert row[1] == "999"

        metrics = db_conn.execute(
            "SELECT metric_name, metric_value FROM source_metrics ORDER BY metric_name"
        ).fetchall()
        metric_dict = {m[0]: m[1] for m in metrics}
        assert metric_dict["effective_vo2max"] == 48.5
        assert metric_dict["vdot"] == 44.2
        assert metric_dict["marathon_shape"] == 92.5

    @patch("src.sync.runalyze.api.get")
    def test_race_prediction_stored(self, mock_get, db_conn, sample_config):
        """race_prediction이 source_metrics에 JSON으로 저장되는지 확인."""
        import json
        now = datetime.now().isoformat()
        mock_get.side_effect = [
            [{"id": 1001, "datetime": now, "distance": 10000, "s": 3000}],
            {"race_prediction_5000": 1200, "race_prediction_10000": 2520, "vo2max": 48.0},
        ]
        sync_activities(sample_config, db_conn, days=7)
        row = db_conn.execute(
            "SELECT metric_json FROM source_metrics WHERE metric_name='race_prediction'"
        ).fetchone()
        assert row is not None
        pred = json.loads(row[0])
        assert pred.get("5k") == 1200

    @patch("src.sync.runalyze.api.get")
    def test_daily_fitness_updated(self, mock_get, db_conn, sample_config):
        """daily_fitness에 runalyze 피트니스 지표가 저장되는지 확인."""
        now = datetime.now().isoformat()
        mock_get.side_effect = [
            [{"id": 1002, "datetime": now, "distance": 10000, "s": 3000}],
            {"vo2max": 49.0, "vdot": 45.0, "marathon_shape": 95.0},
        ]
        sync_activities(sample_config, db_conn, days=7)
        row = db_conn.execute(
            "SELECT runalyze_evo2max, runalyze_vdot, runalyze_marathon_shape "
            "FROM daily_fitness WHERE source='runalyze'"
        ).fetchone()
        assert row is not None
        assert row[0] == pytest.approx(49.0)
        assert row[1] == pytest.approx(45.0)
        assert row[2] == pytest.approx(95.0)

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
