"""Strava sync 테스트."""

from datetime import datetime
from unittest.mock import patch, MagicMock

from src.sync.strava import sync_activities, _refresh_token
from src.sync.strava_auth import refresh_token
from src.sync.strava_activity_sync import sync_activity_detail, _sync_activity_streams
from src.sync.strava_athlete_sync import sync_athlete_profile, sync_athlete_stats, sync_gear


class TestRefreshToken:
    @patch("src.sync.strava_auth.api.post")
    def test_skip_if_not_expired(self, mock_post, sample_config):
        """만료 전이면 갱신하지 않음."""
        token = _refresh_token(sample_config)
        assert token == "at_test"
        mock_post.assert_not_called()

    @patch("src.sync.strava_auth.update_service_config")
    @patch("src.sync.strava_auth.api.post")
    def test_refresh_when_expired(self, mock_post, mock_update, sample_config):
        """만료 시 토큰 갱신."""
        sample_config["strava"]["expires_at"] = 0
        mock_post.return_value = {
            "access_token": "new_at",
            "refresh_token": "new_rt",
            "expires_at": 9999999999,
        }
        token = _refresh_token(sample_config)
        assert token == "new_at"
        assert sample_config["strava"]["access_token"] == "new_at"


class TestSyncActivities:
    @patch("src.sync.strava_activity_sync.api.get")
    @patch("src.sync.strava_activity_sync.api.get_with_headers")
    def test_inserts_activity(self, mock_get_headers, mock_get, db_conn, sample_config):
        """활동 1개 삽입 + cadence *2 변환."""
        now = datetime.now().isoformat()
        activity = {
            "id": 456,
            "start_date_local": now,
            "distance": 10000,
            "moving_time": 3000,
            "elapsed_time": 3100,
            "average_heartrate": 152,
            "max_heartrate": 178,
            "average_cadence": 90,
            "total_elevation_gain": 45,
            "calories": 480,
            "name": "Evening Run",
            "type": "Run",
            "sport_type": "Run",
            "kudos_count": 3,
            "achievement_count": 1,
            "pr_count": 0,
        }
        mock_get_headers.return_value = ([activity], {})
        mock_get.side_effect = [
            # 상세 조회
            {"suffer_score": 87, "laps": [], "best_efforts": []},
            # zones
            [],
            # 스트림
            [{"type": "heartrate", "data": [140, 150, 160]}],
        ]

        with patch("src.sync.strava_activity_sync.refresh_token", return_value="at_test"):
            count = sync_activities(sample_config, db_conn, days=7)

        assert count == 1

        row = db_conn.execute(
            "SELECT source, avg_cadence, name, sport_type FROM activity_summaries"
        ).fetchone()
        assert row[0] == "strava"
        assert row[1] == 180  # Strava cadence * 2
        assert row[2] == "Evening Run"
        assert row[3] == "Run"

    @patch("src.sync.strava_activity_sync.api.get")
    @patch("src.sync.strava_activity_sync.api.get_with_headers")
    def test_stores_suffer_score(self, mock_get_headers, mock_get, db_conn, sample_config):
        """suffer_score가 activity_summaries에 저장됨."""
        now = datetime.now().isoformat()
        activity = {
            "id": 457, "start_date_local": now,
            "distance": 5000, "moving_time": 1500,
            "type": "Run", "suffer_score": 55,
        }
        mock_get_headers.return_value = ([activity], {})
        mock_get.side_effect = [{"suffer_score": 55, "laps": [], "best_efforts": []}, [], []]

        with patch("src.sync.strava_activity_sync.refresh_token", return_value="at_test"):
            sync_activities(sample_config, db_conn, days=7)

        row = db_conn.execute(
            "SELECT suffer_score FROM activity_summaries WHERE source='strava'"
        ).fetchone()
        assert row[0] == 55

    @patch("src.sync.strava_activity_sync.api.get")
    @patch("src.sync.strava_activity_sync.api.get_with_headers")
    def test_stores_streams_in_db(self, mock_get_headers, mock_get, db_conn, sample_config):
        """스트림이 activity_streams 테이블에 저장됨 (파일 아님)."""
        now = datetime.now().isoformat()
        activity = {
            "id": 458, "start_date_local": now,
            "distance": 5000, "moving_time": 1500,
            "type": "Run",
        }
        mock_get_headers.return_value = ([activity], {})
        mock_get.side_effect = [
            {"suffer_score": 60, "laps": [], "best_efforts": []},
            [],
            [{"type": "heartrate", "data": [140, 150]}, {"type": "distance", "data": [0, 100]}],
        ]

        with patch("src.sync.strava_activity_sync.refresh_token", return_value="at_test"):
            sync_activities(sample_config, db_conn, days=7)

        rows = db_conn.execute(
            "SELECT stream_type FROM activity_streams WHERE source='strava' ORDER BY stream_type"
        ).fetchall()
        stream_types = {r[0] for r in rows}
        assert "heartrate" in stream_types
        assert "distance" in stream_types

    @patch("src.sync.strava_activity_sync.api.get")
    @patch("src.sync.strava_activity_sync.api.get_with_headers")
    def test_stores_best_efforts(self, mock_get_headers, mock_get, db_conn, sample_config):
        """best_efforts가 activity_best_efforts 테이블에 저장됨."""
        now = datetime.now().isoformat()
        activity = {
            "id": 459, "start_date_local": now,
            "distance": 10000, "moving_time": 2800,
            "type": "Run",
        }
        mock_get_headers.return_value = ([activity], {})
        mock_get.side_effect = [
            {
                "suffer_score": 70,
                "laps": [],
                "best_efforts": [
                    {"name": "5k", "distance": 5000, "elapsed_time": 1320,
                     "moving_time": 1320, "start_index": 0, "end_index": 200, "pr_rank": 1},
                    {"name": "10k", "distance": 10000, "elapsed_time": 2800,
                     "moving_time": 2800, "start_index": 0, "end_index": 400},
                ],
            },
            [],
            [],
        ]

        with patch("src.sync.strava_activity_sync.refresh_token", return_value="at_test"):
            sync_activities(sample_config, db_conn, days=7)

        rows = db_conn.execute(
            "SELECT name, elapsed_sec, pr_rank FROM activity_best_efforts WHERE source='strava' ORDER BY name"
        ).fetchall()
        assert len(rows) == 2
        names = [r[0] for r in rows]
        assert "5k" in names
        assert "10k" in names
        five_k = next(r for r in rows if r[0] == "5k")
        assert five_k[1] == 1320
        assert five_k[2] == 1

    @patch("src.sync.strava_activity_sync.api.get")
    @patch("src.sync.strava_activity_sync.api.get_with_headers")
    def test_stores_laps(self, mock_get_headers, mock_get, db_conn, sample_config):
        """laps가 activity_laps 테이블에 저장됨."""
        now = datetime.now().isoformat()
        activity = {
            "id": 460, "start_date_local": now,
            "distance": 10000, "moving_time": 2800,
            "type": "Run",
        }
        mock_get_headers.return_value = ([activity], {})
        mock_get.side_effect = [
            {
                "suffer_score": 70,
                "best_efforts": [],
                "laps": [
                    {"lap_index": 1, "distance": 1000, "elapsed_time": 280,
                     "average_heartrate": 150, "average_cadence": 90},
                    {"lap_index": 2, "distance": 1000, "elapsed_time": 275,
                     "average_heartrate": 155, "average_cadence": 91},
                ],
            },
            [],
            [],
        ]

        with patch("src.sync.strava_activity_sync.refresh_token", return_value="at_test"):
            sync_activities(sample_config, db_conn, days=7)

        laps = db_conn.execute(
            "SELECT lap_index, avg_cadence FROM activity_laps WHERE source='strava' ORDER BY lap_index"
        ).fetchall()
        assert len(laps) == 2
        assert laps[0][1] == 180  # cadence * 2


class TestSyncActivityZones:
    @patch("src.sync.strava_activity_sync.api.get")
    @patch("src.sync.strava_activity_sync.api.get_with_headers")
    def test_stores_zones_in_metrics(self, mock_get_headers, mock_get, db_conn, sample_config):
        """zones API 결과가 activity_detail_metrics에 저장됨."""
        now = datetime.now().isoformat()
        activity = {"id": 461, "start_date_local": now, "distance": 5000, "moving_time": 1500, "type": "Run"}
        mock_get_headers.return_value = ([activity], {})
        mock_get.side_effect = [
            {"suffer_score": 60, "laps": [], "best_efforts": []},
            [{"type": "heartrate", "score": 42, "distribution_buckets": [{"time": 120}, {"time": 300}]}],
            [],
        ]

        with patch("src.sync.strava_activity_sync.refresh_token", return_value="at_test"):
            sync_activities(sample_config, db_conn, days=7)

        row = db_conn.execute(
            "SELECT metric_value FROM activity_detail_metrics WHERE source='strava' AND metric_name='heartrate_zone_score'"
        ).fetchone()
        assert row is not None
        assert row[0] == 42.0

    @patch("src.sync.strava_activity_sync.api.get")
    @patch("src.sync.strava_activity_sync.api.get_with_headers")
    def test_stores_workout_type_trainer_commute(self, mock_get_headers, mock_get, db_conn, sample_config):
        """workout_type, trainer, commute 필드가 activity_summaries에 저장됨."""
        now = datetime.now().isoformat()
        activity = {
            "id": 462, "start_date_local": now, "distance": 5000, "moving_time": 1500,
            "type": "Run", "workout_type": 11, "trainer": True, "commute": False,
        }
        mock_get_headers.return_value = ([activity], {})
        mock_get.side_effect = [{"laps": [], "best_efforts": []}, [], []]

        with patch("src.sync.strava_activity_sync.refresh_token", return_value="at_test"):
            sync_activities(sample_config, db_conn, days=7)

        row = db_conn.execute(
            "SELECT workout_type, trainer, commute FROM activity_summaries WHERE source='strava'"
        ).fetchone()
        assert row[0] == 11
        assert row[1] == 1
        assert row[2] is None


class TestSyncAthleteProfile:
    def test_sync_athlete_profile(self, db_conn):
        """선수 프로필 저장 테스트."""
        with patch("src.sync.strava_athlete_sync.api.get") as mock_get:
            mock_get.return_value = {
                "id": 123456,
                "firstname": "John",
                "lastname": "Doe",
                "city": "Seoul",
                "country": "South Korea",
                "sex": "M",
                "weight": 70.5,
                "ftp": 280,
            }
            sync_athlete_profile(db_conn, {"Authorization": "Bearer test"})

        row = db_conn.execute(
            "SELECT firstname, lastname, ftp FROM athlete_profile WHERE source='strava'"
        ).fetchone()
        assert row is not None
        assert row[0] == "John"
        assert row[1] == "Doe"
        assert row[2] == 280

    def test_sync_athlete_stats(self, db_conn):
        """선수 통계 저장 테스트."""
        with patch("src.sync.strava_athlete_sync.api.get") as mock_get:
            mock_get.return_value = {
                "recent_run_totals": {"count": 5, "distance": 50000, "elapsed_time": 18000},
                "ytd_run_totals": {"count": 50, "distance": 400000, "elapsed_time": 144000},
                "all_run_totals": {"count": 500, "distance": 3000000, "elapsed_time": 1080000, "elevation_gain": 50000},
            }
            sync_athlete_stats(db_conn, 123456, {"Authorization": "Bearer test"}, "2026-03-24")

        row = db_conn.execute(
            "SELECT all_run_count, ytd_run_count, recent_run_count FROM athlete_stats WHERE source='strava'"
        ).fetchone()
        assert row is not None
        assert row[0] == 500
        assert row[1] == 50
        assert row[2] == 5

    def test_sync_gear(self, db_conn):
        """기어 저장 테스트."""
        with patch("src.sync.strava_athlete_sync.api.get") as mock_get:
            mock_get.return_value = {
                "id": "g12345",
                "name": "Nike React",
                "brand_name": "Nike",
                "model_name": "React Infinity",
                "distance": 500000,
                "retired": False,
            }
            sync_gear(db_conn, "g12345", {"Authorization": "Bearer test"})

        row = db_conn.execute(
            "SELECT name, brand, retired FROM gear WHERE source='strava'"
        ).fetchone()
        assert row is not None
        assert row[0] == "Nike React"
        assert row[1] == "Nike"
        assert row[2] == 0
