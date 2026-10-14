"""활동 상세 tz_estimated 플래그 (TZ-8)."""
import json

from src.services.activity_detail_service import get_activity_detail


def _row(conn, sid, tz_source):
    cur = conn.execute("INSERT INTO activity_summaries (source, source_id, activity_type, start_time)"
                       " VALUES ('strava', ?, 'running', '2026-05-01T09:30:00')", (sid,))
    conn.execute("INSERT INTO source_payloads (source, entity_type, entity_id, activity_id, payload)"
                 " VALUES ('strava','csv_export',?,?,?)", (sid, cur.lastrowid, json.dumps({"tz_source": tz_source})))
    return cur.lastrowid


def test_tz_estimated_only_for_fallback(db_conn):
    a = _row(db_conn, "a", "fallback")
    b = _row(db_conn, "b", "peer_direct:garmin")
    assert get_activity_detail(db_conn, a)["tz_estimated"] is True
    assert get_activity_detail(db_conn, b)["tz_estimated"] is False
