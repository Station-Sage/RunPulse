"""DoD #11: orchestrator.full_sync + sync_jobs 기록."""
import sqlite3
from unittest.mock import MagicMock, patch

from src.db_setup import create_tables
from src.sync.orchestrator import full_sync


def _conn():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    return c


SAMPLE_GARMIN_ACTIVITY = {
    "activityId": 55555,
    "activityName": "Test Run",
    "activityType": {"typeKey": "running"},
    "startTimeLocal": "2026-04-01 09:00:00",
    "distance": 5000.0,
    "duration": 1500.0,
    "averageHR": 145,
    "maxHR": 170,
}


class TestFullSync:
    def test_no_clients_all_skipped(self):
        """API 클라이언트 없으면 garmin skip, 나머지 fail/skip."""
        conn = _conn()
        results = full_sync(conn, sources=["garmin"], api_clients={})

        assert "garmin" in results
        assert results["garmin"][0].status == "skipped"

    def test_garmin_sync_records_job(self):
        """garmin sync 후 sync_jobs에 기록."""
        conn = _conn()
        api = MagicMock()
        api.get_activities_by_date.return_value = [SAMPLE_GARMIN_ACTIVITY]
        api.get_activity.return_value = None
        api.get_sleep_data.return_value = {}
        api.get_hrv_data.return_value = {}
        api.get_body_battery.return_value = []
        api.get_stress_data.return_value = {}
        api.get_user_summary.return_value = {}
        api.get_training_readiness.return_value = {}

        with patch("src.sync.garmin_activity_sync.RateLimiter") as MockRL, \
             patch("src.sync.garmin_wellness_sync.RateLimiter") as MockRL2:
            MockRL.return_value = MagicMock(
                pre_request=MagicMock(),
                post_request=MagicMock(),
                handle_rate_limit=MagicMock(return_value=False),
                policy=MagicMock(backoff_base=1, backoff_multiplier=1),
                _consecutive_429=0,
            )
            MockRL2.return_value = MockRL.return_value

            results = full_sync(
                conn, sources=["garmin"],
                api_clients={"garmin": api},
                days=1,
            )

        assert "garmin" in results
        jobs = conn.execute("SELECT source, job_type, status FROM sync_jobs").fetchall()
        assert len(jobs) >= 1
        sources = {j[0] for j in jobs}
        assert "garmin" in sources

    def test_multi_source_sync(self):
        """여러 소스 sync → 각각 결과 반환."""
        conn = _conn()
        results = full_sync(
            conn,
            sources=["garmin", "strava", "intervals", "runalyze"],
            api_clients={},
            configs={},
        )

        assert len(results) == 4
        for source in ["garmin", "strava", "intervals", "runalyze"]:
            assert source in results

    def test_dedup_runs_after_sync(self):
        """full_sync 완료 후 dedup이 실행됨 (에러 없이)."""
        conn = _conn()
        # 수동으로 중복 가능한 데이터 삽입
        conn.execute(
            "INSERT INTO activity_summaries (source, source_id, activity_type, start_time, distance_m) "
            "VALUES ('garmin', 'g1', 'running', '2026-04-01T08:00:00', 10000)"
        )
        conn.execute(
            "INSERT INTO activity_summaries (source, source_id, activity_type, start_time, distance_m) "
            "VALUES ('strava', 's1', 'running', '2026-04-01T08:01:00', 10020)"
        )
        conn.commit()

        results = full_sync(conn, sources=[], api_clients={})

        gids = conn.execute(
            "SELECT DISTINCT matched_group_id FROM activity_summaries WHERE matched_group_id IS NOT NULL"
        ).fetchall()
        assert len(gids) == 1

    def test_sync_jobs_have_dates(self):
        """sync_jobs에 from_date, to_date 기록."""
        conn = _conn()
        full_sync(conn, sources=["garmin"], api_clients={})

        job = conn.execute("SELECT from_date, to_date FROM sync_jobs").fetchone()
        if job:
            assert job[0] is not None
            assert job[1] is not None
