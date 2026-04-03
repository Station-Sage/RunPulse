"""DoD #6: Garmin activity sync 흐름 — mock API 기반."""
import sqlite3
from unittest.mock import MagicMock

from src.db_setup import create_tables
from src.sync.garmin_activity_sync import sync


def _conn():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    return c


def _mock_api(activities=None, detail=None, streams=None):
    api = MagicMock()
    api.get_activities_by_date.return_value = activities or []
    api.get_activity.return_value = detail
    api.get_activity_splits.return_value = streams
    return api


SAMPLE_ACTIVITY = {
    "activityId": 12345,
    "activityName": "Morning Run",
    "activityType": {"typeKey": "running"},
    "startTimeLocal": "2026-04-01 08:00:00",
    "distance": 10000.0,
    "duration": 3000.0,
    "movingDuration": 2900.0,
    "elapsedDuration": 3100.0,
    "averageSpeed": 3.33,
    "maxSpeed": 5.0,
    "averageHR": 150,
    "maxHR": 175,
    "averageRunningCadenceInStepsPerMinute": 180,
    "maxRunningCadenceInStepsPerMinute": 192,
    "averagePower": 250.0,
    "maxPower": 300.0,
    "elevationGain": 120.0,
    "elevationLoss": 115.0,
    "calories": 600,
    "aerobicTrainingEffect": 3.5,
    "anaerobicTrainingEffect": 1.2,
    "activityTrainingLoad": 145.0,
}

SAMPLE_DETAIL = {
    "activityId": 12345,
    "summaryDTO": {
        "averageSpeed": 3.33,
        "maxSpeed": 5.0,
        "averageHR": 150,
        "maxHR": 175,
        "trainingEffect": 3.5,
        "anaerobicTrainingEffect": 1.2,
        "activityTrainingLoad": 145.0,
        "vO2MaxValue": 52.0,
        "averagePower": 250.0,
        "normalizedPower": 260.0,
        "hrTimeInZone": [120, 300, 600, 500, 180],
        "powerTimeInZone": [60, 200, 400, 300, 100],
    },
    "activityDetailMetrics": [
        {"metrics": {"directTimestamp": 0, "directHeartRate": 120}},
    ],
}


class TestGarminActivitySync:
    def test_sync_empty_list(self):
        """활동 없으면 total=0, success."""
        conn = _conn()
        api = _mock_api()
        result = sync(conn, api, days=7, _sleep_fn=lambda _: None)
        assert result.status == "success"
        assert result.total_items == 0
        assert result.synced_count == 0

    def test_sync_one_activity(self):
        """활동 1개 sync → activity_summaries + source_payloads + metric_store 기록."""
        conn = _conn()
        api = _mock_api(activities=[SAMPLE_ACTIVITY], detail=SAMPLE_DETAIL)
        result = sync(conn, api, days=7, _sleep_fn=lambda _: None)

        assert result.status == "success"
        assert result.total_items == 1
        assert result.synced_count == 1
        assert result.api_calls >= 2  # list + detail

        # activity_summaries 확인
        row = conn.execute("SELECT source, source_id, distance_m FROM activity_summaries").fetchone()
        assert row[0] == "garmin"
        assert row[1] == "12345"
        assert row[2] == 10000.0

        # source_payloads 확인
        payloads = conn.execute("SELECT entity_type FROM source_payloads WHERE source='garmin'").fetchall()
        types = {r[0] for r in payloads}
        assert "activity_summary" in types
        assert "activity_detail" in types

        # metric_store 확인
        metrics = conn.execute("SELECT COUNT(*) FROM metric_store WHERE scope_type='activity'").fetchone()
        assert metrics[0] > 0

    def test_sync_skip_unchanged(self):
        """같은 활동 두 번 sync → 두 번째는 skip."""
        conn = _conn()
        api = _mock_api(activities=[SAMPLE_ACTIVITY], detail=SAMPLE_DETAIL)

        r1 = sync(conn, api, days=7, _sleep_fn=lambda _: None)
        assert r1.synced_count == 1

        r2 = sync(conn, api, days=7, _sleep_fn=lambda _: None)
        assert r2.skipped_count == 1
        assert r2.synced_count == 0

    def test_sync_with_streams(self):
        """include_streams=True → streams 요청."""
        conn = _conn()
        streams_data = {"lapDTOs": [], "activityDetailMetrics": []}
        api = _mock_api(activities=[SAMPLE_ACTIVITY], detail=SAMPLE_DETAIL, streams=streams_data)

        result = sync(conn, api, days=7, include_streams=True, _sleep_fn=lambda _: None)
        assert result.synced_count == 1
        assert result.api_calls >= 3  # list + detail + streams

    def test_sync_rate_limit_error(self):
        """429 에러 시 partial/failed 상태."""
        conn = _conn()
        api = MagicMock()
        api.get_activities_by_date.side_effect = Exception("429 Too Many Requests")

        result = sync(conn, api, days=7, _sleep_fn=lambda _: None)
        assert result.status == "failed"

    def test_sync_detail_failure_continues(self):
        """detail fetch 실패해도 core는 저장되고 계속 진행."""
        conn = _conn()
        api = _mock_api(activities=[SAMPLE_ACTIVITY])
        api.get_activity.side_effect = Exception("timeout")

        result = sync(conn, api, days=7, _sleep_fn=lambda _: None)
        assert result.synced_count == 1

        row = conn.execute("SELECT COUNT(*) FROM activity_summaries").fetchone()
        assert row[0] == 1

    def test_primary_resolution(self):
        """sync 후 metric_store에 is_primary 설정됨."""
        conn = _conn()
        api = _mock_api(activities=[SAMPLE_ACTIVITY], detail=SAMPLE_DETAIL)
        sync(conn, api, days=7, _sleep_fn=lambda _: None)

        primaries = conn.execute(
            "SELECT COUNT(*) FROM metric_store WHERE is_primary = 1"
        ).fetchone()
        assert primaries[0] > 0
