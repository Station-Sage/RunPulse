"""activity_counts 단위 테스트 (HSR-12)."""
from src.services.activity_counts import activity_counts
from src.services.sync_state_service import get_sync_state


def _ins(conn, source, sid, atype, start):
    conn.execute("INSERT INTO activity_summaries (source, source_id, activity_type, start_time)"
                 " VALUES (?,?,?,?)", (source, sid, atype, start))


def test_counts_use_running_family_not_like(db_conn):
    _ins(db_conn, "garmin", "1", "running", "2026-05-01T07:00:00")
    _ins(db_conn, "garmin", "2", "treadmill_running", "2026-05-02T07:00:00")
    _ins(db_conn, "garmin", "3", "cycling", "2026-05-03T07:00:00")
    _ins(db_conn, "strava", "4", "running", "2026-05-04T07:00:00")
    c = activity_counts(db_conn)
    assert c["canonical_total"] <= 4 and c["canonical_total"] >= c["canonical_running"] >= 1
    assert c["raw_by_source"] == {"garmin": 3, "strava": 1}


def test_empty_db(db_conn):
    assert activity_counts(db_conn) == {"canonical_total": 0, "canonical_running": 0, "raw_by_source": {}}


def test_sync_state_activity_count_matches(db_conn):
    _ins(db_conn, "garmin", "1", "running", "2026-05-01T07:00:00")
    _ins(db_conn, "garmin", "3", "cycling", "2026-05-03T07:00:00")
    st = get_sync_state(db_conn, {})
    assert st["activity_count"] == activity_counts(db_conn)["canonical_running"] == 1
