"""DoD #7: Garmin wellness sync 6 endpoint — mock API 기반."""
import sqlite3
from unittest.mock import MagicMock

from src.db_setup import create_tables
from src.sync.garmin_wellness_sync import sync


def _conn():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    return c


def _mock_api():
    api = MagicMock()
    # sleep — extractor가 sleep_day 최상위에서 overallScore를 찾음
    api.get_sleep_data.return_value = {
        "overallScore": 82,
        "sleepTimeSeconds": 27000,
        "sleepStartTimestampGMT": "2026-04-01T14:00:00.0",
        "sleepScores": {"overall": 82},
    }
    api.get_hrv_data.return_value = {
        "hrvSummary": {"lastNightAvg": 48, "weeklyAvg": 52, "restingHeartRate": 50}
    }
    api.get_body_battery.return_value = {
        "bodyBatteryHigh": 75, "bodyBatteryLow": 50,
    }
    api.get_stress_data.return_value = {
        "avgStressLevel": 32, "maxStressLevel": 70,
    }
    api.get_user_summary.return_value = {
        "restingHeartRate": 50, "totalSteps": 8500,
        "activeKilocalories": 400, "totalKilocalories": 2200,
    }
    api.get_training_readiness.return_value = {
        "score": 75, "sleepScore": 80, "recoveryScore": 70, "hrvScore": 65,
    }
    return api


class TestGarminWellnessSync:
    def test_sync_one_day(self):
        """1일 sync → daily_wellness + metric_store 기록."""
        conn = _conn()
        api = _mock_api()
        result = sync(conn, api, days=1, _sleep_fn=lambda _: None)

        assert result.status == "success"
        assert result.total_items == 1
        assert result.synced_count == 1
        assert result.api_calls == 6  # 6 endpoints

        # core 필드 확인 — extractor가 실제로 채우는 필드만 검증
        row = conn.execute(
            "SELECT hrv_weekly_avg, hrv_last_night, resting_hr, avg_stress, steps "
            "FROM daily_wellness"
        ).fetchone()
        assert row is not None
        assert row[0] == 52   # hrv_weekly_avg
        assert row[1] == 48   # hrv_last_night
        assert row[2] == 50   # resting_hr
        assert row[3] == 32   # avg_stress
        assert row[4] == 8500 # steps

    def test_sync_multi_day(self):
        """3일 sync → 3행."""
        conn = _conn()
        api = _mock_api()
        result = sync(conn, api, days=3, _sleep_fn=lambda _: None)

        assert result.total_items == 3
        count = conn.execute("SELECT COUNT(*) FROM daily_wellness").fetchone()[0]
        assert count == 3

    def test_sync_skip_unchanged(self):
        """같은 날 두 번 → 두 번째 skip."""
        conn = _conn()
        api = _mock_api()

        r1 = sync(conn, api, days=1, _sleep_fn=lambda _: None)
        assert r1.synced_count == 1

        r2 = sync(conn, api, days=1, _sleep_fn=lambda _: None)
        assert r2.skipped_count == 1
        assert r2.synced_count == 0

    def test_sync_stores_raw_payloads(self):
        """6 endpoint raw payload 저장."""
        conn = _conn()
        api = _mock_api()
        sync(conn, api, days=1, _sleep_fn=lambda _: None)

        types = {r[0] for r in conn.execute(
            "SELECT entity_type FROM source_payloads WHERE source='garmin'"
        ).fetchall()}
        for ep in ["sleep_day", "hrv_day", "body_battery_day", "stress_day",
                    "user_summary_day", "training_readiness"]:
            assert ep in types, f"{ep} not in source_payloads"

    def test_sync_metrics_created(self):
        """wellness metrics → metric_store."""
        conn = _conn()
        api = _mock_api()
        sync(conn, api, days=1, _sleep_fn=lambda _: None)

        metrics = conn.execute(
            "SELECT COUNT(*) FROM metric_store WHERE scope_type='daily'"
        ).fetchone()
        assert metrics[0] > 0

    def test_sync_partial_endpoint_failure(self):
        """일부 endpoint 실패해도 나머지는 저장."""
        conn = _conn()
        api = _mock_api()
        api.get_hrv_data.side_effect = Exception("timeout")
        api.get_training_readiness.side_effect = Exception("500")

        result = sync(conn, api, days=1, _sleep_fn=lambda _: None)
        assert result.synced_count == 1

        row = conn.execute("SELECT steps FROM daily_wellness").fetchone()
        assert row is not None
        assert row[0] == 8500
