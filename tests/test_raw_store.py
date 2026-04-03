"""raw_store 단위 테스트."""

import sqlite3
from src.db_setup import create_tables
from src.sync.raw_store import upsert_raw_payload, update_raw_activity_id


def _conn():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    return c


class TestUpsertRawPayload:
    def test_new_payload_returns_true(self):
        conn = _conn()
        ok = upsert_raw_payload(conn, "garmin", "activity_summary", "123", {"a": 1})
        assert ok is True

    def test_same_payload_returns_false(self):
        conn = _conn()
        upsert_raw_payload(conn, "garmin", "activity_summary", "123", {"a": 1})
        ok = upsert_raw_payload(conn, "garmin", "activity_summary", "123", {"a": 1})
        assert ok is False

    def test_changed_payload_returns_true(self):
        conn = _conn()
        upsert_raw_payload(conn, "garmin", "activity_summary", "123", {"a": 1})
        ok = upsert_raw_payload(conn, "garmin", "activity_summary", "123", {"a": 2})
        assert ok is True

    def test_row_count(self):
        conn = _conn()
        upsert_raw_payload(conn, "garmin", "activity_summary", "123", {"a": 1})
        upsert_raw_payload(conn, "garmin", "activity_summary", "123", {"a": 2})
        count = conn.execute("SELECT COUNT(*) FROM source_payloads").fetchone()[0]
        assert count == 1  # UPSERT → 1행


class TestUpdateRawActivityId:
    def test_sets_activity_id(self):
        conn = _conn()
        upsert_raw_payload(conn, "garmin", "activity_summary", "123", {"x": 1})
        update_raw_activity_id(conn, "garmin", "activity_summary", "123", 42)
        row = conn.execute(
            "SELECT activity_id FROM source_payloads WHERE entity_id = '123'"
        ).fetchone()
        assert row[0] == 42
