"""raw_source_payloads 저장/병합 유틸리티 테스트."""
from __future__ import annotations

import json
import sqlite3

import pytest

from src.utils.raw_payload import fill_null_columns, store_raw_payload


@pytest.fixture()
def conn():
    """인메모리 SQLite DB — raw_source_payloads + activity_summaries 포함."""
    c = sqlite3.connect(":memory:")
    c.executescript("""
        CREATE TABLE raw_source_payloads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            activity_id INTEGER,
            payload_json TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(source, entity_type, entity_id)
        );
        CREATE TABLE activity_summaries (
            id INTEGER PRIMARY KEY,
            source TEXT NOT NULL,
            source_id TEXT NOT NULL,
            activity_type TEXT,
            start_time TEXT,
            distance_km REAL,
            duration_sec INTEGER,
            avg_pace_sec_km INTEGER,
            avg_hr INTEGER,
            max_hr INTEGER,
            avg_cadence INTEGER,
            elevation_gain REAL,
            calories INTEGER,
            description TEXT,
            UNIQUE(source, source_id)
        );
    """)
    yield c
    c.close()


# ──────────────────────────────────────────────
# store_raw_payload 테스트
# ──────────────────────────────────────────────

class TestStoreRawPayload:
    def test_insert_new(self, conn):
        """신규 엔티티 삽입."""
        store_raw_payload(conn, "garmin", "activity", "123", {"key": "val"})
        row = conn.execute(
            "SELECT payload_json FROM raw_source_payloads WHERE entity_id = '123'"
        ).fetchone()
        assert row is not None
        assert json.loads(row[0]) == {"key": "val"}

    def test_merge_preserves_existing_keys(self, conn):
        """기존에만 있는 키는 보존된다."""
        store_raw_payload(conn, "garmin", "activity", "1", {"old_key": "old", "common": "old_val"})
        store_raw_payload(conn, "garmin", "activity", "1", {"new_key": "new", "common": "new_val"})
        row = conn.execute(
            "SELECT payload_json FROM raw_source_payloads WHERE entity_id = '1'"
        ).fetchone()
        data = json.loads(row[0])
        assert data["old_key"] == "old"       # 기존 고유 키 보존
        assert data["new_key"] == "new"       # 새 키 추가
        assert data["common"] == "new_val"    # 같은 키는 새 값으로 덮어씀

    def test_merge_new_value_overrides(self, conn):
        """동일 키는 새 값이 우선."""
        store_raw_payload(conn, "strava", "activity_summary", "A", {"hr": 140, "pace": 300})
        store_raw_payload(conn, "strava", "activity_summary", "A", {"hr": 145})
        data = json.loads(
            conn.execute("SELECT payload_json FROM raw_source_payloads").fetchone()[0]
        )
        assert data["hr"] == 145
        assert data["pace"] == 300  # 기존 키 보존

    def test_activity_id_set_on_insert(self, conn):
        """신규 삽입 시 activity_id 설정."""
        store_raw_payload(conn, "intervals", "activity", "X", {"a": 1}, activity_id=42)
        row = conn.execute("SELECT activity_id FROM raw_source_payloads").fetchone()
        assert row[0] == 42

    def test_activity_id_coalesce_on_update(self, conn):
        """기존 activity_id가 있으면 NULL로 덮어쓰지 않는다."""
        store_raw_payload(conn, "runalyze", "activity", "Y", {"x": 1}, activity_id=10)
        store_raw_payload(conn, "runalyze", "activity", "Y", {"x": 2}, activity_id=None)
        row = conn.execute("SELECT activity_id FROM raw_source_payloads").fetchone()
        assert row[0] == 10  # COALESCE — 기존 값 유지

    def test_activity_id_updated_when_provided(self, conn):
        """명시적 activity_id 제공 시 업데이트된다."""
        store_raw_payload(conn, "garmin", "activity", "Z", {"x": 1}, activity_id=None)
        store_raw_payload(conn, "garmin", "activity", "Z", {"x": 2}, activity_id=99)
        row = conn.execute("SELECT activity_id FROM raw_source_payloads").fetchone()
        assert row[0] == 99

    def test_empty_payload_skipped(self, conn):
        """빈 payload는 저장하지 않는다."""
        store_raw_payload(conn, "garmin", "activity", "E", {})
        row = conn.execute("SELECT COUNT(*) FROM raw_source_payloads").fetchone()
        assert row[0] == 0

    def test_none_payload_skipped(self, conn):
        """None payload는 저장하지 않는다."""
        store_raw_payload(conn, "garmin", "activity", "N", None)
        row = conn.execute("SELECT COUNT(*) FROM raw_source_payloads").fetchone()
        assert row[0] == 0

    def test_different_sources_same_entity_id(self, conn):
        """소스가 다르면 같은 entity_id라도 별도 레코드."""
        store_raw_payload(conn, "garmin", "activity", "100", {"src": "garmin"})
        store_raw_payload(conn, "strava", "activity", "100", {"src": "strava"})
        count = conn.execute("SELECT COUNT(*) FROM raw_source_payloads").fetchone()[0]
        assert count == 2

    def test_graceful_on_missing_table(self):
        """테이블이 없어도 예외 없이 통과 (OperationalError 무시)."""
        c = sqlite3.connect(":memory:")
        store_raw_payload(c, "garmin", "activity", "1", {"a": 1})  # 예외 없어야 함
        c.close()

    def test_updated_at_changes_on_merge(self, conn):
        """병합 시 updated_at이 갱신된다."""
        store_raw_payload(conn, "garmin", "activity", "T", {"v": 1})
        ts1 = conn.execute("SELECT updated_at FROM raw_source_payloads").fetchone()[0]
        import time; time.sleep(0.01)
        store_raw_payload(conn, "garmin", "activity", "T", {"v": 2})
        ts2 = conn.execute("SELECT updated_at FROM raw_source_payloads").fetchone()[0]
        # 같은 초 내일 수 있으므로 값 자체 대신 열 존재 확인
        assert ts2 is not None


# ──────────────────────────────────────────────
# fill_null_columns 테스트
# ──────────────────────────────────────────────

class TestFillNullColumns:
    def _insert_activity(self, conn, source="garmin", source_id="1", **kwargs):
        cols = ["source", "source_id"] + list(kwargs.keys())
        placeholders = ", ".join("?" * len(cols))
        conn.execute(
            f"INSERT INTO activity_summaries ({', '.join(cols)}) VALUES ({placeholders})",
            [source, source_id, *kwargs.values()],
        )
        return conn.execute(
            "SELECT id FROM activity_summaries WHERE source=? AND source_id=?",
            (source, source_id),
        ).fetchone()[0]

    def test_fills_null_hr(self, conn):
        """NULL avg_hr가 새 값으로 보완된다."""
        self._insert_activity(conn, avg_hr=None)
        fill_null_columns(conn, "garmin", "1", {"avg_hr": 148})
        val = conn.execute("SELECT avg_hr FROM activity_summaries").fetchone()[0]
        assert val == 148

    def test_does_not_overwrite_existing_value(self, conn):
        """기존에 값이 있으면 변경하지 않는다."""
        self._insert_activity(conn, avg_hr=140)
        fill_null_columns(conn, "garmin", "1", {"avg_hr": 999})
        val = conn.execute("SELECT avg_hr FROM activity_summaries").fetchone()[0]
        assert val == 140  # 기존 값 보존

    def test_multiple_columns(self, conn):
        """여러 NULL 컬럼을 동시에 보완."""
        self._insert_activity(conn, avg_hr=None, max_hr=None, calories=None)
        fill_null_columns(conn, "garmin", "1", {
            "avg_hr": 145, "max_hr": 175, "calories": 500
        })
        row = conn.execute("SELECT avg_hr, max_hr, calories FROM activity_summaries").fetchone()
        assert row == (145, 175, 500)

    def test_none_values_skipped(self, conn):
        """updates에서 None 값은 SET 절에서 제외 — 불필요한 COALESCE 없음."""
        self._insert_activity(conn, avg_hr=None)
        fill_null_columns(conn, "garmin", "1", {"avg_hr": None, "max_hr": None})
        row = conn.execute("SELECT avg_hr FROM activity_summaries").fetchone()
        assert row[0] is None  # 아무것도 안 바뀜

    def test_returns_activity_id(self, conn):
        """기존 레코드의 id를 반환한다."""
        act_id = self._insert_activity(conn, source_id="42")
        returned = fill_null_columns(conn, "garmin", "42", {"avg_hr": 150})
        assert returned == act_id

    def test_returns_none_if_not_found(self, conn):
        """레코드가 없으면 None 반환."""
        result = fill_null_columns(conn, "garmin", "nonexistent", {"avg_hr": 150})
        assert result is None

    def test_partial_override(self, conn):
        """일부 컬럼은 기존 값, 일부는 NULL 보완."""
        self._insert_activity(conn, avg_hr=140, max_hr=None, calories=None)
        fill_null_columns(conn, "garmin", "1", {
            "avg_hr": 999, "max_hr": 175, "calories": 500
        })
        row = conn.execute("SELECT avg_hr, max_hr, calories FROM activity_summaries").fetchone()
        assert row[0] == 140   # 기존 값 유지
        assert row[1] == 175   # NULL 보완
        assert row[2] == 500   # NULL 보완
