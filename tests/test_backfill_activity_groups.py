"""activity_groups 백필 스크립트 테스트."""

import sqlite3
import pytest

from src.db_setup import create_tables, migrate_db
from scripts.backfill_activity_groups import backfill


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    migrate_db(c)
    yield c
    c.close()


def _insert_activity(conn, source, source_id, start_time, distance_m, group_id=None):
    conn.execute(
        "INSERT INTO activity_summaries (source, source_id, start_time, distance_m, matched_group_id) "
        "VALUES (?, ?, ?, ?, ?)",
        (source, source_id, start_time, distance_m, group_id),
    )
    conn.commit()


class TestBackfill:
    def test_backfill_creates_groups(self, conn):
        """matched_group_id가 있는 활동으로부터 activity_groups 행이 생성된다."""
        _insert_activity(conn, "garmin", "g1", "2026-04-01T08:00:00", 10000, "grp-001")
        _insert_activity(conn, "strava", "s1", "2026-04-01T08:01:00", 10050, "grp-001")
        count = backfill(conn)
        assert count == 1
        row = conn.execute("SELECT * FROM activity_groups WHERE group_id = 'grp-001'").fetchone()
        assert row is not None

    def test_backfill_primary_source_priority(self, conn):
        """garmin > intervals > strava > runalyze 우선순위로 primary_source 결정."""
        _insert_activity(conn, "strava", "s1", "2026-04-01T08:01:00", 10000, "grp-002")
        _insert_activity(conn, "garmin", "g1", "2026-04-01T08:00:00", 10000, "grp-002")
        _insert_activity(conn, "intervals", "i1", "2026-04-01T08:02:00", 10000, "grp-002")
        backfill(conn)
        row = conn.execute(
            "SELECT primary_source, member_count FROM activity_groups WHERE group_id = 'grp-002'"
        ).fetchone()
        assert row[0] == "garmin"
        assert row[1] == 3

    def test_backfill_ignores_ungrouped(self, conn):
        """matched_group_id가 NULL인 활동은 백필에서 제외된다."""
        _insert_activity(conn, "garmin", "g1", "2026-04-01T08:00:00", 10000, None)
        count = backfill(conn)
        assert count == 0

    def test_backfill_idempotent(self, conn):
        """백필을 두 번 실행해도 중복 행이 생기지 않는다."""
        _insert_activity(conn, "garmin", "g1", "2026-04-01T08:00:00", 10000, "grp-003")
        _insert_activity(conn, "strava", "s1", "2026-04-01T08:01:00", 10050, "grp-003")
        backfill(conn)
        backfill(conn)
        count = conn.execute("SELECT COUNT(*) FROM activity_groups").fetchone()[0]
        assert count == 1

    def test_backfill_multiple_groups(self, conn):
        """여러 그룹이 올바르게 분리돼 삽입된다."""
        _insert_activity(conn, "garmin", "g1", "2026-04-01T08:00:00", 10000, "grp-A")
        _insert_activity(conn, "strava", "s1", "2026-04-01T08:01:00", 10050, "grp-A")
        _insert_activity(conn, "garmin", "g2", "2026-04-02T09:00:00", 5000, "grp-B")
        _insert_activity(conn, "intervals", "i1", "2026-04-02T09:02:00", 5100, "grp-B")
        count = backfill(conn)
        assert count == 2
        sources = {
            r[0]
            for r in conn.execute("SELECT primary_source FROM activity_groups").fetchall()
        }
        assert sources == {"garmin"}

    def test_backfill_activity_date_from_start_time(self, conn):
        """activity_date가 start_time에서 올바르게 추출된다."""
        _insert_activity(conn, "garmin", "g1", "2026-04-15T08:30:00", 10000, "grp-D")
        backfill(conn)
        row = conn.execute("SELECT activity_date FROM activity_groups WHERE group_id = 'grp-D'").fetchone()
        assert row[0] == "2026-04-15"
