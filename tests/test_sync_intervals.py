"""Intervals.icu sync 테스트."""

from datetime import datetime
from unittest.mock import patch

from src.sync.intervals import sync_activities, sync_wellness
from src.sync.intervals_activity_sync import _sync_activity_intervals, _sync_activity_streams
from src.sync.intervals_athlete_sync import sync_athlete_profile, sync_athlete_stats_snapshot


class TestSyncActivities:
    @patch("src.sync.intervals_activity_sync.api.get")
    def test_inserts_activity(self, mock_get, db_conn, sample_config):
        """활동 1개 삽입 기본 테스트."""
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

        row = db_conn.execute("SELECT source, source_id FROM activity_summaries").fetchone()
        assert row[0] == "intervals"
        assert row[1] == "i789"

        metrics = db_conn.execute(
            "SELECT metric_name FROM activity_detail_metrics ORDER BY metric_name"
        ).fetchall()
        names = [m[0] for m in metrics]
        assert "icu_training_load" in names

    @patch("src.sync.intervals_activity_sync.api.get")
    def test_stores_icu_fields_in_summary(self, mock_get, db_conn, sample_config):
        """icu_* 필드가 activity_summaries 컬럼에 직접 저장됨."""
        now = datetime.now().isoformat()
        mock_get.return_value = [{
            "id": "i790",
            "start_date_local": now,
            "distance": 10000,
            "moving_time": 3000,
            "type": "Run",
            "icu_training_load": 95.5,
            "icu_hrss": 88.3,
            "atl": 55.1,
            "ctl": 42.3,
            "form": -12.8,
            "gap": 280.0,
            "decoupling": 3.5,
            "icu_efficiency_factor": 0.95,
        }]

        sync_activities(sample_config, db_conn, days=7)

        row = db_conn.execute(
            """SELECT icu_training_load, icu_hrss, icu_atl, icu_ctl, icu_tsb,
                      icu_gap, icu_decoupling, icu_efficiency_factor
               FROM activity_summaries WHERE source='intervals'"""
        ).fetchone()
        assert row is not None
        assert abs(row[0] - 95.5) < 0.1
        assert abs(row[1] - 88.3) < 0.1
        assert abs(row[2] - 55.1) < 0.1
        assert abs(row[3] - 42.3) < 0.1
        assert abs(row[4] - (-12.8)) < 0.1
        assert abs(row[5] - 280.0) < 0.1

    @patch("src.sync.intervals_activity_sync.api.get")
    def test_stores_name_not_description(self, mock_get, db_conn, sample_config):
        """활동명이 name 컬럼에 저장됨 (description이 아님)."""
        now = datetime.now().isoformat()
        mock_get.return_value = [{
            "id": "i791",
            "start_date_local": now,
            "distance": 10000,
            "moving_time": 3000,
            "type": "Run",
            "name": "Morning Easy Run",
        }]

        sync_activities(sample_config, db_conn, days=7)

        row = db_conn.execute(
            "SELECT name FROM activity_summaries WHERE source='intervals'"
        ).fetchone()
        assert row[0] == "Morning Easy Run"

    @patch("src.sync.intervals_activity_sync.api.get")
    def test_stores_all_sports(self, mock_get, db_conn, sample_config):
        """런닝 외 스포츠도 저장됨."""
        now = datetime.now().isoformat()
        mock_get.return_value = [
            {"id": "i792", "start_date_local": now, "distance": 30000,
             "moving_time": 3600, "type": "Ride", "sport_type": "VirtualRide", "name": "Zwift Ride"},
            {"id": "i793", "start_date_local": now, "distance": 1500,
             "moving_time": 1200, "type": "Swim", "sport_type": "Swim", "name": "Pool Swim"},
        ]

        count = sync_activities(sample_config, db_conn, days=7)
        assert count == 2

        rows = db_conn.execute(
            "SELECT activity_type FROM activity_summaries WHERE source='intervals' ORDER BY activity_type"
        ).fetchall()
        types = [r[0] for r in rows]
        assert "ride" in types
        assert "swim" in types


class TestSyncWellness:
    @patch("src.sync.intervals_wellness_sync.api.get")
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
            "form": -12.8,
            "rampRate": 1.5,
        }]

        count = sync_wellness(sample_config, db_conn, days=7)
        assert count == 1

        row = db_conn.execute("SELECT hrv_value, resting_hr FROM daily_wellness").fetchone()
        assert row[0] == 42
        assert row[1] == 50

    @patch("src.sync.intervals_wellness_sync.api.get")
    def test_ctl_atl_in_daily_fitness(self, mock_get, db_conn, sample_config):
        """CTL/ATL/TSB가 daily_fitness에 저장됨."""
        mock_get.return_value = [{
            "id": "2026-03-18",
            "ctl": 42.3,
            "atl": 55.1,
            "form": -12.8,
        }]

        sync_wellness(sample_config, db_conn, days=7)

        row = db_conn.execute(
            "SELECT ctl, atl, tsb FROM daily_fitness WHERE source='intervals'"
        ).fetchone()
        assert row is not None
        assert abs(row[0] - 42.3) < 0.01
        assert abs(row[1] - 55.1) < 0.01
        assert abs(row[2] - (-12.8)) < 0.01


class TestSyncAthleteProfile:
    @patch("src.sync.intervals_athlete_sync.api.get")
    def test_sync_athlete_profile(self, mock_get, db_conn, sample_config):
        """선수 프로필 저장 테스트."""
        mock_get.return_value = {
            "id": "i123",
            "name": "Test Runner",
            "country": "Korea",
            "sex": "M",
            "weight": 65.0,
            "ftp": 260,
            "lthr": 172,
            "vo2max": 55.3,
        }

        sync_athlete_profile(sample_config, db_conn)

        row = db_conn.execute(
            "SELECT source_athlete_id, ftp, lthr, vo2max FROM athlete_profile WHERE source='intervals'"
        ).fetchone()
        assert row is not None
        assert row[0] == "i123"
        assert row[1] == 260
        assert row[2] == 172
        assert abs(row[3] - 55.3) < 0.1

    def test_sync_athlete_stats_snapshot(self, db_conn, sample_config):
        """DB 집계 기반 통계 스냅샷 저장 테스트."""
        from datetime import datetime as dt
        # 샘플 활동 삽입
        db_conn.execute(
            """INSERT INTO activity_summaries
               (source, source_id, activity_type, start_time, distance_km, duration_sec)
               VALUES ('intervals', 'i1', 'run', ?, 10.0, 3000)""",
            (dt.now().isoformat(),),
        )
        db_conn.commit()

        sync_athlete_stats_snapshot(sample_config, db_conn)

        row = db_conn.execute(
            "SELECT all_run_count, all_run_distance_km FROM athlete_stats WHERE source='intervals'"
        ).fetchone()
        assert row is not None
        assert row[0] >= 1


class TestStartLatLon:
    @patch("src.sync.intervals_activity_sync.api.get")
    def test_stores_start_latlng(self, mock_get, db_conn, sample_config):
        """start_latlng가 start_lat/start_lon으로 저장됨."""
        now = datetime.now().isoformat()
        mock_get.return_value = [{
            "id": "i850",
            "start_date_local": now,
            "distance": 10000,
            "moving_time": 3000,
            "type": "Run",
            "start_latlng": [37.5665, 126.9780],
        }]

        sync_activities(sample_config, db_conn, days=7)

        row = db_conn.execute(
            "SELECT start_lat, start_lon FROM activity_summaries WHERE source_id='i850'"
        ).fetchone()
        assert row is not None
        assert abs(row[0] - 37.5665) < 0.0001
        assert abs(row[1] - 126.9780) < 0.0001


class TestSyncActivityIntervals:
    @patch("src.sync.intervals_activity_sync.api.get")
    def test_sync_intervals_to_laps(self, mock_get, db_conn, sample_config):
        """Intervals.icu intervals → activity_laps 저장 테스트."""
        # 먼저 activity_summaries에 활동 삽입
        db_conn.execute(
            """INSERT INTO activity_summaries
               (source, source_id, activity_type, start_time)
               VALUES ('intervals', 'i800', 'run', '2026-03-01T08:00:00')"""
        )
        db_conn.commit()
        act_id = db_conn.execute("SELECT id FROM activity_summaries WHERE source_id='i800'").fetchone()[0]

        mock_get.return_value = [
            {"distance": 1000, "moving_time": 280, "average_heartrate": 150, "average_cadence": 90},
            {"distance": 1000, "moving_time": 275, "average_heartrate": 155, "average_cadence": 91},
        ]

        _sync_activity_intervals(db_conn, "i800", act_id, ("API_KEY", "key"), "https://intervals.icu/api/v1/athlete/i123")

        laps = db_conn.execute(
            "SELECT COUNT(*) FROM activity_laps WHERE source='intervals' AND activity_id=?",
            (act_id,),
        ).fetchone()[0]
        assert laps == 2
