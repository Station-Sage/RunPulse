"""metric_priority.py 단위 테스트 — Phase 1 조건 7"""
import sqlite3
import pytest
from src.utils.metric_priority import (
    get_provider_priority, resolve_primary,
    resolve_for_scope, resolve_all_primaries,
)
from src.db_setup import create_tables, migrate_db


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    create_tables(conn)
    migrate_db(conn)
    yield conn
    conn.close()


class TestProviderPriority:
    def test_user_highest(self):
        assert get_provider_priority("user") < get_provider_priority("garmin")

    def test_garmin_before_strava(self):
        assert get_provider_priority("garmin") < get_provider_priority("strava")

    def test_runpulse_ml_before_garmin(self):
        assert get_provider_priority("runpulse:ml") < get_provider_priority("garmin")

    def test_unknown_provider_low_priority(self):
        p = get_provider_priority("unknown_source")
        assert p >= 900  # 매우 낮은 우선순위


class TestResolvePrimary:
    """조건 7: resolve_primary() 테스트"""

    def test_single_provider(self, db):
        db.execute(
            "INSERT INTO metric_store "
            "(scope_type, scope_id, metric_name, provider, numeric_value, category, is_primary) "
            "VALUES ('activity', 'a1', 'hr_avg', 'garmin', 145, 'heart_rate', 0)"
        )
        db.commit()
        resolve_primary(db, "activity", "a1", "hr_avg")
        row = db.execute(
            "SELECT is_primary FROM metric_store "
            "WHERE scope_type='activity' AND scope_id='a1' AND metric_name='hr_avg'"
        ).fetchone()
        assert row[0] == 1

    def test_multi_provider_garmin_wins(self, db):
        for prov, val in [("strava", 140), ("garmin", 145), ("intervals", 142)]:
            db.execute(
                "INSERT INTO metric_store "
                "(scope_type, scope_id, metric_name, provider, numeric_value, category, is_primary) "
                "VALUES ('activity', 'a2', 'hr_avg', ?, ?, 'heart_rate', 0)",
                (prov, val),
            )
        db.commit()
        resolve_primary(db, "activity", "a2", "hr_avg")
        row = db.execute(
            "SELECT provider FROM metric_store "
            "WHERE scope_type='activity' AND scope_id='a2' "
            "AND metric_name='hr_avg' AND is_primary=1"
        ).fetchone()
        assert row[0] == "garmin"

    def test_user_override_wins(self, db):
        for prov, val in [("garmin", 145), ("user", 150)]:
            db.execute(
                "INSERT INTO metric_store "
                "(scope_type, scope_id, metric_name, provider, numeric_value, category, is_primary) "
                "VALUES ('activity', 'a3', 'hr_avg', ?, ?, 'heart_rate', 0)",
                (prov, val),
            )
        db.commit()
        resolve_primary(db, "activity", "a3", "hr_avg")
        row = db.execute(
            "SELECT provider FROM metric_store "
            "WHERE scope_type='activity' AND scope_id='a3' "
            "AND metric_name='hr_avg' AND is_primary=1"
        ).fetchone()
        assert row[0] == "user"

    def test_resolve_for_scope(self, db):
        for metric in ["hr_avg", "hr_max", "cadence_avg"]:
            db.execute(
                "INSERT INTO metric_store "
                "(scope_type, scope_id, metric_name, provider, numeric_value, category, is_primary) "
                "VALUES ('activity', 'a4', ?, 'garmin', 100, 'heart_rate', 0)",
                (metric,),
            )
        db.commit()
        resolve_for_scope(db, "activity", "a4")
        primaries = db.execute(
            "SELECT COUNT(*) FROM metric_store "
            "WHERE scope_type='activity' AND scope_id='a4' AND is_primary=1"
        ).fetchone()[0]
        assert primaries == 3
