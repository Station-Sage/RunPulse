"""DoD #4 (reprocess): Layer 0 → Layer 1/2 재구축 테스트."""
import json
import sqlite3

from src.db_setup import create_tables
from src.sync.reprocess import reprocess_all
from src.utils.db_helpers import upsert_payload


def _conn():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    return c


# ── Garmin fixture ──
GARMIN_SUMMARY = {
    "activityId": 11111,
    "activityName": "Morning Run",
    "activityType": {"typeKey": "running"},
    "startTimeLocal": "2026-04-01 08:00:00",
    "distance": 10000.0,
    "duration": 3000.0,
    "averageHR": 150,
    "maxHR": 175,
    "averageRunningCadenceInStepsPerMinute": 180,
    "elevationGain": 100.0,
    "calories": 600,
    "vO2MaxValue": 52.0,
    "trainingStressScore": 85.0,
}

GARMIN_DETAIL = {
    "activityId": 11111,
    "hrTimeInZone": [120, 300, 600, 500, 180],
    "powerTimeInZone": [60, 200, 400, 300, 100],
    "summaryDTO": {
        "averageSpeed": 3.33,
        "maxSpeed": 5.0,
        "vO2MaxValue": 52.0,
        "averagePower": 250.0,
    },
}

GARMIN_WELLNESS_SLEEP = {
    "overallScore": 85,
    "sleepTimeSeconds": 28000,
}

GARMIN_WELLNESS_HRV = {
    "hrvSummary": {"lastNightAvg": 50, "weeklyAvg": 55, "restingHeartRate": 48},
}

GARMIN_WELLNESS_STRESS = {
    "avgStressLevel": 30,
}

GARMIN_WELLNESS_SUMMARY = {
    "totalSteps": 9000,
    "activeKilocalories": 450,
    "restingHeartRate": 48,
}


def _seed_garmin_activity(conn):
    """source_payloads에 Garmin activity raw 데이터 삽입."""
    upsert_payload(conn, "garmin", "activity_summary", "11111", GARMIN_SUMMARY)
    upsert_payload(
        conn, "garmin", "activity_detail", "11111", GARMIN_DETAIL,
    )
    conn.commit()


def _seed_garmin_wellness(conn, date_str="2026-04-01"):
    """source_payloads에 Garmin wellness raw 데이터 삽입."""
    upsert_payload(conn, "garmin", "sleep_day", date_str, GARMIN_WELLNESS_SLEEP,
                   entity_date=date_str)
    upsert_payload(conn, "garmin", "hrv_day", date_str, GARMIN_WELLNESS_HRV,
                   entity_date=date_str)
    upsert_payload(conn, "garmin", "stress_day", date_str, GARMIN_WELLNESS_STRESS,
                   entity_date=date_str)
    upsert_payload(conn, "garmin", "user_summary_day", date_str, GARMIN_WELLNESS_SUMMARY,
                   entity_date=date_str)
    conn.commit()


class TestReprocessActivity:
    def test_rebuilds_from_raw(self):
        """source_payloads만으로 activity_summaries + metric_store 재구축."""
        conn = _conn()
        _seed_garmin_activity(conn)

        stats = reprocess_all(conn)

        assert stats["activities"] == 1
        assert stats["errors"] == 0

        row = conn.execute(
            "SELECT source, source_id, distance_m FROM activity_summaries"
        ).fetchone()
        assert row[0] == "garmin"
        assert row[1] == "11111"
        assert row[2] == 10000.0

    def test_metrics_rebuilt(self):
        """detail payload → metric_store 재구축."""
        conn = _conn()
        _seed_garmin_activity(conn)

        stats = reprocess_all(conn)

        assert stats["metrics"] > 0
        count = conn.execute(
            "SELECT COUNT(*) FROM metric_store WHERE scope_type = 'activity'"
        ).fetchone()[0]
        assert count > 0

    def test_primary_resolved(self):
        """reprocess 후 is_primary 설정."""
        conn = _conn()
        _seed_garmin_activity(conn)

        reprocess_all(conn)

        primaries = conn.execute(
            "SELECT COUNT(*) FROM metric_store WHERE is_primary = 1"
        ).fetchone()[0]
        assert primaries > 0

    def test_preserves_raw(self):
        """reprocess 후 source_payloads 행 수 변화 없음."""
        conn = _conn()
        _seed_garmin_activity(conn)

        before = conn.execute("SELECT COUNT(*) FROM source_payloads").fetchone()[0]
        reprocess_all(conn)
        after = conn.execute("SELECT COUNT(*) FROM source_payloads").fetchone()[0]

        assert before == after

    def test_clears_derived_only(self):
        """clear_first=True → source_payloads 유지, Layer 1/2만 삭제 후 재구축."""
        conn = _conn()
        _seed_garmin_activity(conn)

        # 첫 reprocess
        reprocess_all(conn)
        act_count_1 = conn.execute("SELECT COUNT(*) FROM activity_summaries").fetchone()[0]
        assert act_count_1 == 1

        # 두 번째 reprocess (clear_first=True)
        reprocess_all(conn, clear_first=True)
        act_count_2 = conn.execute("SELECT COUNT(*) FROM activity_summaries").fetchone()[0]
        assert act_count_2 == 1  # 삭제 후 재구축이므로 동일

        raw_count = conn.execute("SELECT COUNT(*) FROM source_payloads").fetchone()[0]
        assert raw_count == 2  # summary + detail 유지

    def test_no_clear_accumulates(self):
        """clear_first=False → 기존 데이터 위에 upsert."""
        conn = _conn()
        _seed_garmin_activity(conn)

        reprocess_all(conn)
        reprocess_all(conn, clear_first=False)

        # UPSERT이므로 중복 없이 1행
        act_count = conn.execute("SELECT COUNT(*) FROM activity_summaries").fetchone()[0]
        assert act_count == 1


class TestReprocessWellness:
    def test_wellness_rebuilt(self):
        """wellness payloads → daily_wellness 재구축."""
        conn = _conn()
        _seed_garmin_wellness(conn)

        stats = reprocess_all(conn)

        assert stats["wellness"] >= 1
        row = conn.execute("SELECT steps, resting_hr FROM daily_wellness").fetchone()
        assert row is not None
        assert row[0] == 9000
        assert row[1] == 48

    def test_wellness_metrics_rebuilt(self):
        """wellness → metric_store."""
        conn = _conn()
        _seed_garmin_wellness(conn)

        stats = reprocess_all(conn)

        count = conn.execute(
            "SELECT COUNT(*) FROM metric_store WHERE scope_type = 'daily'"
        ).fetchone()[0]
        assert count > 0


class TestReprocessSourceFilter:
    def test_source_filter(self):
        """source='garmin' 지정 시 garmin만 재처리."""
        conn = _conn()
        _seed_garmin_activity(conn)
        # strava도 하나 넣기
        upsert_payload(conn, "strava", "activity_summary", "s1", {
            "id": 99999, "name": "Strava Run", "type": "Run",
            "start_date": "2026-04-01T10:00:00Z",
            "distance": 5000.0, "moving_time": 1500,
        })
        conn.commit()

        stats = reprocess_all(conn, source="garmin")

        # garmin만 처리됨
        assert stats["activities"] == 1
        row = conn.execute(
            "SELECT COUNT(*) FROM activity_summaries WHERE source = 'strava'"
        ).fetchone()[0]
        assert row == 0  # strava는 처리 안 됨


class TestReprocessDedup:
    def test_dedup_runs(self):
        """reprocess 후 dedup 실행 — cross-source 매칭."""
        conn = _conn()
        # garmin
        upsert_payload(conn, "garmin", "activity_summary", "g1", {
            "activityId": 1, "activityName": "Run",
            "activityType": {"typeKey": "running"},
            "startTimeLocal": "2026-04-01 08:00:00",
            "distance": 10000.0, "duration": 3000.0,
        })
        # strava — 같은 시간, 비슷한 거리
        upsert_payload(conn, "strava", "activity_summary", "s1", {
            "id": 2, "name": "Run", "type": "Run",
            "start_date": "2026-04-01T08:01:00Z",
            "start_date_local": "2026-04-01T08:01:00",
            "distance": 10020.0, "moving_time": 3000,
        })
        conn.commit()

        reprocess_all(conn)

        gids = conn.execute(
            "SELECT DISTINCT matched_group_id FROM activity_summaries "
            "WHERE matched_group_id IS NOT NULL"
        ).fetchall()
        assert len(gids) == 1
