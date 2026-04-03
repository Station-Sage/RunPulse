"""db_helpers.py 단위 테스트 — Phase 1 조건 8, 9"""
import sqlite3
import json
import pytest
from src.db_setup import create_tables, migrate_db
from src.utils.db_helpers import (
    upsert_payload,
    upsert_activity,
    upsert_metric,
    upsert_metrics_batch,
    upsert_daily_wellness,
    upsert_daily_fitness,
    get_primary_metrics,
    get_all_providers,
    get_db_status,
)


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_tables(conn)
    migrate_db(conn)
    yield conn
    conn.close()


class TestUpsertActivitySummary:

    def test_insert_new(self, db):
        data = {
            "source": "garmin", "source_id": "g001",
            "start_time": "2025-01-15T08:00:00",
            "activity_type": "running",
            "distance_m": 10000, "duration_sec": 3000,
            "avg_hr": 150, "name": "Morning Run",
        }
        row_id = upsert_activity(db, data)
        db.commit()
        row = db.execute(
            "SELECT * FROM activity_summaries WHERE source='garmin' AND source_id='g001'"
        ).fetchone()
        assert row is not None
        assert row["distance_m"] == 10000

    def test_upsert_updates(self, db):
        data = {
            "source": "garmin", "source_id": "g001",
            "start_time": "2025-01-15T08:00:00",
            "activity_type": "running",
            "distance_m": 10000, "duration_sec": 3000,
        }
        upsert_activity(db, data)
        data["distance_m"] = 10500
        upsert_activity(db, data)
        db.commit()
        row = db.execute(
            "SELECT distance_m FROM activity_summaries "
            "WHERE source='garmin' AND source_id='g001'"
        ).fetchone()
        assert row["distance_m"] == 10500

    def test_no_duplicate_rows(self, db):
        data = {
            "source": "garmin", "source_id": "g002",
            "start_time": "2025-01-16T07:00:00",
            "activity_type": "running",
            "distance_m": 5000, "duration_sec": 1500,
        }
        upsert_activity(db, data)
        upsert_activity(db, data)
        db.commit()
        cnt = db.execute(
            "SELECT COUNT(*) FROM activity_summaries "
            "WHERE source='garmin' AND source_id='g002'"
        ).fetchone()[0]
        assert cnt == 1


class TestUpsertMetric:
    """조건 8: upsert_metric()"""

    def test_insert_single(self, db):
        upsert_metric(db, "activity", "a1", "hr_avg", "garmin",
                       numeric_value=155, category="heart_rate")
        db.commit()
        row = db.execute(
            "SELECT numeric_value FROM metric_store "
            "WHERE scope_id='a1' AND metric_name='hr_avg'"
        ).fetchone()
        assert row["numeric_value"] == 155

    def test_batch_upsert(self, db):
        metrics = [
            {"metric_name": f"metric_{i}", "provider": "garmin",
             "numeric_value": float(i), "category": "test"}
            for i in range(50)
        ]
        count = upsert_metrics_batch(db, "activity", "a1", metrics)
        db.commit()
        cnt = db.execute(
            "SELECT COUNT(*) FROM metric_store WHERE scope_id='a1'"
        ).fetchone()[0]
        assert cnt == 50
        assert count == 50

    def test_upsert_updates_value(self, db):
        upsert_metric(db, "activity", "a1", "cadence", "garmin",
                       numeric_value=170, category="dynamics")
        upsert_metric(db, "activity", "a1", "cadence", "garmin",
                       numeric_value=175, category="dynamics")
        db.commit()
        row = db.execute(
            "SELECT numeric_value FROM metric_store "
            "WHERE scope_id='a1' AND metric_name='cadence' AND provider='garmin'"
        ).fetchone()
        assert row["numeric_value"] == 175


class TestUpsertDailyWellness:
    """조건 8: upsert_daily_wellness()"""

    def test_insert(self, db):
        data = {
            "date": "2025-01-15",
            "resting_hr": 52,
            "sleep_score": 80,
        }
        upsert_daily_wellness(db, data)
        db.commit()
        row = db.execute(
            "SELECT * FROM daily_wellness WHERE date='2025-01-15'"
        ).fetchone()
        assert row is not None
        assert row["resting_hr"] == 52

    def test_merge_keeps_first_non_null(self, db):
        upsert_daily_wellness(db, {
            "date": "2025-01-15", "resting_hr": 52,
        })
        upsert_daily_wellness(db, {
            "date": "2025-01-15", "sleep_score": 85,
        })
        db.commit()
        row = db.execute(
            "SELECT resting_hr, sleep_score FROM daily_wellness "
            "WHERE date='2025-01-15'"
        ).fetchone()
        assert row["resting_hr"] == 52
        assert row["sleep_score"] == 85


class TestGetPrimaryMetrics:
    """조건 9: get_primary_metrics(), get_all_providers()"""

    def _seed_metrics(self, db):
        for prov, val, primary in [("garmin", 150, 0), ("strava", 148, 0), ("user", 152, 1)]:
            upsert_metric(db, "activity", "a10", "hr_avg", prov,
                          numeric_value=val, category="heart_rate")
            if primary:
                db.execute(
                    "UPDATE metric_store SET is_primary=1 "
                    "WHERE scope_id='a10' AND metric_name='hr_avg' AND provider=?",
                    (prov,),
                )
        db.commit()

    def test_get_primary_returns_list(self, db):
        self._seed_metrics(db)
        primaries = get_primary_metrics(db, "activity", "a10")
        assert isinstance(primaries, list)
        assert len(primaries) >= 1
        assert primaries[0]["metric_name"] == "hr_avg"

    def test_get_all_providers(self, db):
        self._seed_metrics(db)
        providers = get_all_providers(db, "activity", "a10", "hr_avg")
        assert len(providers) == 3
        names = {p["provider"] for p in providers}
        assert {"garmin", "strava", "user"} == names

    def test_get_primary_empty_scope(self, db):
        result = get_primary_metrics(db, "activity", "nonexistent")
        assert len(result) == 0


class TestUpsertPayload:
    """upsert_payload 기본 동작"""

    def test_insert_and_no_change(self, db):
        payload = {"key": "value", "num": 42}
        row_id, is_new = upsert_payload(db, "garmin", "activity", "g001", payload)
        db.commit()
        assert is_new is True

        row_id2, is_new2 = upsert_payload(db, "garmin", "activity", "g001", payload)
        assert is_new2 is False
        assert row_id == row_id2

    def test_update_on_change(self, db):
        upsert_payload(db, "garmin", "activity", "g001", {"v": 1})
        db.commit()
        _, changed = upsert_payload(db, "garmin", "activity", "g001", {"v": 2})
        assert changed is True


class TestDailyFitness:
    """upsert_daily_fitness 기본 동작"""

    def test_insert(self, db):
        row_id = upsert_daily_fitness(db, "2025-01-15", "garmin", ctl=45.2, atl=52.1, tsb=-6.9)
        db.commit()
        assert row_id > 0

    def test_upsert_coalesce(self, db):
        upsert_daily_fitness(db, "2025-01-15", "garmin", ctl=45.2)
        upsert_daily_fitness(db, "2025-01-15", "garmin", atl=52.1)
        db.commit()
        row = db.execute(
            "SELECT ctl, atl FROM daily_fitness WHERE date='2025-01-15' AND source='garmin'"
        ).fetchone()
        assert row["ctl"] == 45.2
        assert row["atl"] == 52.1


class TestDbStatus:
    """get_db_status"""

    def test_returns_dict(self, db):
        status = get_db_status(db)
        assert isinstance(status, dict)
        assert "activity_summaries_count" in status
        assert "metric_store_count" in status
        assert "primary_violations" in status
