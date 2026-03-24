"""Garmin sync 테스트."""

import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock

from src.sync.garmin import sync_activities, sync_wellness, sync_garmin


class TestSyncActivities:
    @patch("src.sync.garmin_auth.Garmin")
    @patch("src.sync.garmin_activity_sync.time.sleep")
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
                "averageSpeed": 3.33,
                "maxSpeed": 5.10,
                "averageRunCadence": 180,
                "maxRunCadence": 192,
                "averageStrideLength": 1.12,
                "avgVerticalRatio": 8.4,
                "avgGroundContactTime": 248,
                "hrTimeInZone": [300, 600, 900, 700, 500],
                "powerTimeInZone": [100, 200, 300, 400, 500],
            }
        }
        mock_garmin_cls.return_value = mock_client

        count = sync_activities(sample_config, db_conn, days=7)
        assert count == 1

        row = db_conn.execute("SELECT source, source_id, distance_km FROM activity_summaries").fetchone()
        assert row[0] == "garmin"
        assert row[1] == "123"
        assert abs(row[2] - 10.0) < 0.01

        payload_rows = db_conn.execute(
            "SELECT entity_type, entity_id FROM raw_source_payloads WHERE source='garmin' ORDER BY entity_type"
        ).fetchall()
        assert ("activity_detail", "123") in payload_rows
        assert ("activity_summary", "123") in payload_rows

        metrics = db_conn.execute(
            "SELECT metric_name, metric_value FROM activity_detail_metrics ORDER BY metric_name"
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
        assert metric_dict["avg_speed"] == pytest.approx(3.33)
        assert metric_dict["max_speed"] == pytest.approx(5.10)
        assert metric_dict["avg_run_cadence"] == pytest.approx(180)
        assert metric_dict["max_run_cadence"] == pytest.approx(192)
        assert metric_dict["avg_stride_length"] == pytest.approx(1.12)
        assert metric_dict["avg_vertical_ratio"] == pytest.approx(8.4)
        assert metric_dict["avg_ground_contact_time"] == pytest.approx(248)
        assert metric_dict["hr_zone_time_1"] == pytest.approx(300)
        assert metric_dict["hr_zone_time_2"] == pytest.approx(600)
        assert metric_dict["hr_zone_time_3"] == pytest.approx(900)
        assert metric_dict["hr_zone_time_4"] == pytest.approx(700)
        assert metric_dict["hr_zone_time_5"] == pytest.approx(500)
        assert metric_dict["power_zone_time_1"] == pytest.approx(100)
        assert metric_dict["power_zone_time_2"] == pytest.approx(200)
        assert metric_dict["power_zone_time_3"] == pytest.approx(300)
        assert metric_dict["power_zone_time_4"] == pytest.approx(400)
        assert metric_dict["power_zone_time_5"] == pytest.approx(500)
        assert metric_dict["avg_power"] == pytest.approx(250)
        assert metric_dict["normalized_power"] == pytest.approx(265)
        assert metric_dict["steps"] == pytest.approx(1345)

        # garmin vo2max가 daily_fitness에도 저장됨
        row = db_conn.execute(
            "SELECT garmin_vo2max FROM daily_fitness WHERE source='garmin'"
        ).fetchone()
        assert row is not None
        assert row[0] == pytest.approx(48.5)

    @patch("src.sync.garmin_auth.Garmin")
    @patch("src.sync.garmin_activity_sync.time.sleep")
    def test_skip_duplicate(self, mock_sleep, mock_garmin_cls, db_conn, sample_config):
        """이미 존재하는 활동은 건너뜀."""
        now = datetime.now().isoformat()
        db_conn.execute(
            "INSERT INTO activity_summaries (source, source_id, start_time) VALUES ('garmin', '123', ?)",
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
    @patch("src.sync.garmin_auth.Garmin")
    @patch("src.sync.garmin_wellness_sync.time.sleep")
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
                "awakeSleepSeconds": 1200,
                "lightSleepSeconds": 14400,
                "deepSleepSeconds": 5400,
                "remSleepSeconds": 7800,
                "sleepStartTimestampLocal": "2026-03-20T23:00:00",
                "sleepEndTimestampLocal": "2026-03-21T07:00:00",
                "restlessMomentsCount": 14,
                "averageRespiration": 13.2,
                "averageSpO2": 96.0,
            }
        }
        mock_client.get_hrv_data.return_value = {
            "hrvSummary": {
                "lastNightAvg": 45,
                "sdnn": 62,
                "weeklyAvg": 49,
                "status": "balanced",
                "baselineLow": 42,
                "baselineHigh": 58,
            }
        }
        mock_client.get_body_battery.return_value = [{
            "bodyBatteryValuesArray": [[0, 62], [180000, 80], [360000, 55]],
            "charged": 20,
            "drained": 40,
        }]
        mock_client.get_stress_data.return_value = {
            "avgStressLevel": 35,
            "maxStressLevel": 78,
            "restStressDuration": 180,
            "lowStressDuration": 240,
            "mediumStressDuration": 120,
            "highStressDuration": 60,
            "stressValuesArray": [[0, 15], [180000, 28], [360000, 42], [540000, 78]],
        }
        mock_client.get_respiration_data.return_value = {
            "averageRespiration": 13.4,
            "minRespiration": 11.2,
            "maxRespiration": 16.8,
        }
        mock_client.get_spo2_data.return_value = {
            "averageSpO2": 96.5,
            "minSpO2": 93.0,
            "maxSpO2": 99.0,
        }
        mock_client.get_training_readiness.return_value = {
            "score": 78,
            "sleepScore": 82,
            "recoveryScore": 74,
            "hrvScore": 69,
        }
        mock_client.get_body_composition.return_value = {
            "weightKg": 69.4,
            "bodyFatPercentage": 14.8,
            "bodyWaterPercentage": 61.2,
            "skeletalMuscleMass": 31.5,
            "boneMass": 3.4,
            "bmi": 22.1,
        }
        mock_client.get_rhr_day.return_value = {"restingHeartRate": 52}
        mock_garmin_cls.return_value = mock_client

        count = sync_wellness(sample_config, db_conn, days=1)
        assert count == 1

        row = db_conn.execute(
            "SELECT sleep_score, hrv_value, hrv_sdnn, body_battery, resting_hr, avg_sleeping_hr, stress_avg, readiness_score, steps, weight_kg FROM daily_wellness"
        ).fetchone()
        assert row[0] == 85
        assert row[1] == 45
        assert row[2] == pytest.approx(62)
        assert row[3] == 80
        assert row[4] == 51
        assert row[5] == 47
        assert row[6] == 35
        assert row[7] == 72
        assert row[8] == 9876
        assert row[9] == pytest.approx(69.4)



        detail_rows = db_conn.execute(
            "SELECT metric_name, metric_value, metric_json "
            "FROM daily_detail_metrics WHERE source='garmin' ORDER BY metric_name"
        ).fetchall()
        detail_map = {name: (value, metric_json) for name, value, metric_json in detail_rows}

        assert detail_map["sleep_stage_awake_sec"][0] == 1200
        assert detail_map["sleep_stage_light_sec"][0] == 14400
        assert detail_map["sleep_stage_deep_sec"][0] == 5400
        assert detail_map["sleep_stage_rem_sec"][0] == 7800

        assert detail_map["overnight_hrv_avg"][0] == 45
        assert detail_map["overnight_hrv_sdnn"][0] == 62
        assert detail_map["hrv_weekly_avg"][0] == 49
        assert "balanced" in detail_map["hrv_status"][1]

        assert detail_map["body_battery_start"][0] == 62
        assert detail_map["body_battery_end"][0] == 55
        assert detail_map["body_battery_min"][0] == 55
        assert detail_map["body_battery_max"][0] == 80
        # body_battery_timeline은 [[timestamp_ms, level], ...] 형태로 저장됨
        import json as _json
        bb_timeline = _json.loads(detail_map["body_battery_timeline"][1])
        assert any(pair[1] == 80 for pair in bb_timeline if len(pair) > 1)

        assert detail_map["stress_max"][0] == 78
        assert detail_map["stress_rest_duration"][0] == 180
        assert detail_map["stress_low_duration"][0] == 240
        assert detail_map["stress_medium_duration"][0] == 120
        assert detail_map["stress_high_duration"][0] == 60
        assert "78" in detail_map["stress_timeline"][1]

        assert "2026-03-20T23:00:00" in detail_map["sleep_start_timestamp"][1]
        assert "2026-03-21T07:00:00" in detail_map["sleep_end_timestamp"][1]

        assert detail_map["sleep_total_sec"][0] == 28800
        assert detail_map["sleep_restless_moments"][0] == 14
        assert detail_map["sleep_avg_respiration"][0] == 13.2
        assert detail_map["sleep_avg_spo2"][0] == 96.0
        assert '"dailySleepDTO"' in detail_map["sleep_summary_json"][1]

        assert detail_map["hrv_baseline_low"][0] == 42
        assert detail_map["hrv_baseline_high"][0] == 58
        assert '"hrvSummary"' in detail_map["hrv_summary_json"][1]

        assert detail_map["body_battery_samples"][0] == 3
        assert detail_map["body_battery_delta"][0] == -7
        assert '"sample_count": 3' in detail_map["body_battery_summary_json"][1]

        assert detail_map["stress_avg"][0] == 35
        assert '"maxStressLevel": 78' in detail_map["stress_summary_json"][1]

        assert detail_map["respiration_avg"][0] == 13.4
        assert detail_map["respiration_min"][0] == 11.2
        assert detail_map["respiration_max"][0] == 16.8
        assert '"averageRespiration": 13.4' in detail_map["respiration_summary_json"][1]

        assert detail_map["spo2_avg"][0] == 96.5
        assert detail_map["spo2_min"][0] == 93.0
        assert detail_map["spo2_max"][0] == 99.0
        assert '"averageSpO2": 96.5' in detail_map["spo2_summary_json"][1]

        assert detail_map["training_readiness_score"][0] == 78
        assert detail_map["training_readiness_sleep_score"][0] == 82
        assert detail_map["training_readiness_recovery_score"][0] == 74
        assert detail_map["training_readiness_hrv_score"][0] == 69
        assert '"score": 78' in detail_map["training_readiness_summary_json"][1]

        assert detail_map["body_weight_kg"][0] == 69.4
        assert detail_map["body_fat_pct"][0] == 14.8
        assert detail_map["body_water_pct"][0] == 61.2
        assert detail_map["skeletal_muscle_mass_kg"][0] == 31.5
        assert detail_map["bone_mass_kg"][0] == 3.4
        assert detail_map["bmi"][0] == 22.1
        assert '"weightKg": 69.4' in detail_map["body_composition_summary_json"][1]

        payload_types = {
            row[0]
            for row in db_conn.execute(
                "SELECT entity_type FROM raw_source_payloads WHERE source='garmin' ORDER BY entity_type"
            ).fetchall()
        }

        assert "respiration_day" in payload_types
        assert "spo2_day" in payload_types
        assert (
            "training_readiness_day" in payload_types
            or "morning_training_readiness_day" in payload_types
        )
        assert "body_composition_day" in payload_types
        assert "sleep_day" in payload_types
        assert "hrv_day" in payload_types
        assert "body_battery_day" in payload_types
        assert "stress_day" in payload_types
        assert "rhr_day" in payload_types
