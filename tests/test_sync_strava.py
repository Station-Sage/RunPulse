"""Strava sync 테스트."""

from datetime import datetime
from unittest.mock import patch, MagicMock

from src.sync.strava import sync_activities, _refresh_token


class TestRefreshToken:
    @patch("src.sync.strava.api.post")
    def test_skip_if_not_expired(self, mock_post, sample_config):
        """만료 전이면 갱신하지 않음."""
        token = _refresh_token(sample_config)
        assert token == "at_test"
        mock_post.assert_not_called()

    @patch("src.sync.strava.api.post")
    def test_refresh_when_expired(self, mock_post, sample_config):
        """만료 시 토큰 갱신."""
        sample_config["strava"]["expires_at"] = 0
        mock_post.return_value = {
            "access_token": "new_at",
            "refresh_token": "new_rt",
            "expires_at": 9999999999,
        }

        with patch("builtins.open", MagicMock()):
            with patch("src.sync.strava.Path.exists", return_value=False):
                token = _refresh_token(sample_config)

        assert token == "new_at"
        assert sample_config["strava"]["access_token"] == "new_at"


class TestSyncActivities:
    @patch("src.sync.strava.api.get")
    @patch("src.sync.strava.api.get_with_headers")
    def test_inserts_activity(self, mock_get_headers, mock_get, db_conn, sample_config):
        now = datetime.now().isoformat()
        activity = {
            "id": 456,
            "start_date_local": now,
            "distance": 10000,
            "moving_time": 3000,
            "average_heartrate": 152,
            "max_heartrate": 178,
            "average_cadence": 90,
            "total_elevation_gain": 45,
            "calories": 480,
            "name": "Evening Run",
            "type": "Run",
        }
        # get_with_headers returns (data, headers) tuple
        mock_get_headers.return_value = ([activity], {})
        mock_get.side_effect = [
            # 상세 (페이지 2 — 빈 목록으로 종료 트리거)
            {"suffer_score": 87},
            # 스트림
            [{"type": "heartrate", "data": [140, 150, 160]}],
            # 빈 페이지 (루프 종료용)
            [],
        ]

        with patch("src.sync.strava._refresh_token", return_value="at_test"):
            with patch("src.sync.strava._STREAMS_DIR") as mock_dir:
                mock_dir.mkdir = MagicMock()
                mock_dir.__truediv__ = MagicMock(return_value=MagicMock())
                with patch("builtins.open", MagicMock()):
                    count = sync_activities(sample_config, db_conn, days=7)

        assert count == 1

        row = db_conn.execute("SELECT source, avg_cadence FROM activity_summaries").fetchone()
        assert row[0] == "strava"
        assert row[1] == 180  # Strava cadence * 2
