"""Garmin sync 테스트."""

import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock

from src.sync.garmin import sync_activities, sync_wellness, sync_garmin


class TestSyncActivities:
    @patch("src.sync.garmin.Garmin")
    @patch("src.sync.garmin.time.sleep")
    def test_inserts_activity(self, mock_sleep, mock_garmin_cls, db_conn, sample_config):
        now = datetime.now().isoformat()
        mock_client = MagicMock()
        mock_client.get_activities.return_value = [
            {
                "activityId": 123,
                "startTimeLocal": now,
                "distance": 10000,
                "duration": 3000,
                "averageHR": 150,
                "maxHR": 175,
                "averageRunningCadenceInStepsPerMinute": 180,
                "elevationGain": 50,
                "calories": 500,
                "activityName": "Morning Run",
                "activityType": {"typeKey": "running"},
            }
        ]
        mock_client.get_activity.return_value = {
            "summaryDTO": {
                "aerobicTrainingEffect": 3.2,
                "anaerobicTrainingEffect": 1.5,
                "activityTrainingLoad": 156,
                "vO2MaxValue": 48.5,
                "averagePower": 250,
                "normalizedPower": 265,
                "steps": 1345,
            }
        }
        mock_garmin_cls.return_value = mock_client

        count = sync_activities(sample_config, db_conn, days=7)
        assert count == 1

        row = db_conn.execute("SELECT source, source_id, distance_km FROM activities").fetchone()
        assert row[0] == "garmin"
        assert row[1] == "123"
        assert abs(row[2] - 10.0) < 0.01

        payload_rows = db_conn.execute(
            "SELECT entity_type, entity_id FROM source_payloads WHERE source='garmin' ORDER BY entity_type"
        ).fetchall()
        assert ("activity_detail", "123") in payload_rows
        assert ("activity_summary", "123") in payload_rows

        metrics = db_conn.execute(
            "SELECT metric_name, metric_value FROM source_metrics ORDER BY metric_name"
        ).fetchall()
        metric_dict = {m[0]: m[1] for m in metrics}

        # 하위호환 alias + 신규 분리 키 모두 존재
        assert "training_effect" in metric_dict          # backward compat
        assert "training_effect_aerobic" in metric_dict  # aerobic TE
        assert "training_effect_anaerobic" in metric_dict  # anaerobic TE
        assert metric_dict["training_effect"] == pytest.approx(3.2)
        assert metric_dict["training_effect_aerobic"] == pytest.approx(3.2)
        assert "vo2max" in metric_dict
        assert metric_dict["avg_power"] == pytest.approx(250)
        assert metric_dict["normalized_power"] == pytest.approx(265)
        assert metric_dict["steps"] == pytest.approx(1345)
        assert metric_dict["avg_power"] == pytest.approx(250)
        assert metric_dict["normalized_power"] == pytest.approx(265)
        assert metric_dict["steps"] == pytest.approx(1345)

        # garmin vo2max가 daily_fitness에도 저장됨
        row = db_conn.execute(
            "SELECT garmin_vo2max FROM daily_fitness WHERE source='garmin'"
        ).fetchone()
        assert row is not None
        assert row[0] == pytest.approx(48.5)

    @patch("src.sync.garmin.Garmin")
    @patch("src.sync.garmin.time.sleep")
    def test_skip_duplicate(self, mock_sleep, mock_garmin_cls, db_conn, sample_config):
        """이미 존재하는 활동은 건너뜀."""
        now = datetime.now().isoformat()
        db_conn.execute(
            "INSERT INTO activities (source, source_id, start_time) VALUES ('garmin', '123', ?)",
            (now,),
        )

        mock_client = MagicMock()
        mock_client.get_activities.return_value = [
            {"activityId": 123, "startTimeLocal": now, "distance": 10000, "duration": 3000,
             "activityType": {"typeKey": "running"}},
        ]
        mock_garmin_cls.return_value = mock_client

        count = sync_activities(sample_config, db_conn, days=7)
        assert count == 0


class TestSyncWellness:
    @patch("src.sync.garmin.Garmin")
    @patch("src.sync.garmin.time.sleep")
    def test_inserts_wellness(self, mock_sleep, mock_garmin_cls, db_conn, sample_config):
        mock_client = MagicMock()
        mock_client.get_sleep_data.return_value = {
            "readinessScore": 72,
            "weightKg": 69.4,
            "steps": 9876,
            "dailySleepDTO": {
                "sleepScores": {"overall": {"value": 85}},
                "sleepTimeSeconds": 28800,
                "averageHeartRate": 47,
                "restingHeartRate": 51,
            }
        }
        mock_client.get_hrv_data.return_value = {"hrvSummary": {"lastNightAvg": 45}}
        mock_client.get_body_battery.return_value = [{"bodyBatteryLevel": 80}]
        mock_client.get_stress_data.return_value = {"averageStressLevel": 35}
        mock_client.get_rhr_day.return_value = {"restingHeartRate": 52}
        mock_garmin_cls.return_value = mock_client

        count = sync_wellness(sample_config, db_conn, days=1)
        assert count == 1

        row = db_conn.execute(
            "SELECT sleep_score, hrv_value, body_battery, resting_hr, avg_sleeping_hr, readiness_score, steps, weight_kg FROM daily_wellness"
        ).fetchone()
        assert row[0] == 85
        assert row[1] == 45
        assert row[2] == 80
        assert row[3] == 51
        assert row[4] == 47
        assert row[5] == 72
        assert row[6] == 9876
        assert row[7] == pytest.approx(69.4)

        payload_types = {
            row[0]
            for row in db_conn.execute(
                "SELECT entity_type FROM source_payloads WHERE source='garmin' ORDER BY entity_type"
            ).fetchall()
        }
        assert "sleep_day" in payload_types
        assert "hrv_day" in payload_types
        assert "body_battery_day" in payload_types
        assert "stress_day" in payload_types
        assert "rhr_day" in payload_types
