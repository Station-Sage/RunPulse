"""SyncResult 단위 테스트."""

from src.sync.sync_result import SyncResult


class TestSyncResult:
    def test_defaults(self):
        r = SyncResult(source="garmin", job_type="activity")
        assert r.status == "success"
        assert r.total_items == 0
        assert r.is_rate_limited() is False

    def test_rate_limited(self):
        r = SyncResult(source="garmin", job_type="activity", retry_after="2026-04-03T12:00:00Z")
        assert r.is_rate_limited() is True

    def test_merge(self):
        r1 = SyncResult(source="garmin", job_type="activity", synced_count=3, api_calls=5)
        r2 = SyncResult(source="garmin", job_type="activity", synced_count=2, api_calls=3,
                         error_count=1, last_error="timeout")
        r1.merge(r2)
        assert r1.synced_count == 5
        assert r1.api_calls == 8
        assert r1.error_count == 1
        assert r1.last_error == "timeout"

    def test_merge_failed_becomes_partial(self):
        r1 = SyncResult(source="garmin", job_type="activity", synced_count=2)
        r2 = SyncResult(source="garmin", job_type="activity", status="failed")
        r1.merge(r2)
        assert r1.status == "partial"

    def test_to_sync_job_dict(self):
        r = SyncResult(source="strava", job_type="activity", synced_count=5, total_items=10)
        d = r.to_sync_job_dict("2026-03-27", "2026-04-03")
        assert d["source"] == "strava"
        assert d["completed_items"] == 5
        assert d["from_date"] == "2026-03-27"
        assert "id" in d  # UUID
