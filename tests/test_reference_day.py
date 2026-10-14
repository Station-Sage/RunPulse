"""reference_today: 최근 활동 오프셋 기반 '오늘' 판정 (TZ T5)."""
import json
import sqlite3
from datetime import datetime, timezone

from src.utils.reference_day import reference_offset, reference_today


def _conn():
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE activity_summaries (id INTEGER PRIMARY KEY, start_time TEXT)")
    c.execute("CREATE TABLE source_payloads (source TEXT, entity_type TEXT, entity_id TEXT,"
              " activity_id INTEGER, payload TEXT)")
    return c


def _garmin(c, aid, utc, local):
    c.execute("INSERT INTO activity_summaries VALUES (?, ?)", (aid, local))
    c.execute("INSERT INTO source_payloads VALUES ('garmin','activity_summary',?,?,?)",
              (str(aid), aid, json.dumps({"startTimeGMT": utc, "startTimeLocal": local})))


def test_activity_tz_crosses_date():
    c = _conn()
    _garmin(c, 1, "2026-10-01T10:00:00", "2026-10-01T19:00:00")
    now = datetime(2026, 10, 14, 20, 0, tzinfo=timezone.utc)  # KST 10-15 05:00
    assert reference_today(c, now) == ("2026-10-15", "activity_tz")


def test_falls_back_to_older_activity():
    c = _conn()
    _garmin(c, 1, "2026-09-01T10:00:00", "2026-09-01T19:00:00")
    c.execute("INSERT INTO activity_summaries VALUES (2, '2026-10-01T19:00:00')")
    assert reference_offset(c) == 9 * 3600


def test_strava_csv_offset():
    c = _conn()
    c.execute("INSERT INTO activity_summaries VALUES (1, '2026-10-01T19:00:00')")
    c.execute("INSERT INTO source_payloads VALUES ('strava','csv_export','9',1,?)",
              (json.dumps({"start_date_utc": "2026-10-01T10:00:00"}),))
    assert reference_offset(c) == 9 * 3600


def test_server_local_fallback():
    c = _conn()
    assert reference_today(c)[1] == "server_local"
