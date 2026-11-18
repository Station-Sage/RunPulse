"""Garmin 강제 재수집 백필 잡 — 완료 활동 재처리·이어하기·종목 필터·429 중단."""
import sqlite3

from src.db_setup import create_tables
from src.sync.garmin_activity_sync import sync
from src.sync.garmin_backfill_job import pending_ids, run_backfill
from tests.test_garmin_activity_sync import (
    SAMPLE_ACTIVITY, SAMPLE_DETAIL, _STREAMS, _mock_api,
)

_NOSLEEP = lambda _: None  # noqa: E731


def _seeded():
    conn = sqlite3.connect(":memory:")
    create_tables(conn)
    api = _mock_api(activities=[SAMPLE_ACTIVITY], detail=SAMPLE_DETAIL, streams=_STREAMS)
    sync(conn, api, days=7, include_streams=True, _sleep_fn=_NOSLEEP)
    return conn, api


def test_pending_filters_sport_and_done():
    conn, _ = _seeded()
    assert [i for i, _ in pending_ids(conn, set(), 10)] == ["12345"]
    assert pending_ids(conn, set(), 10, sport="other") == []
    assert pending_ids(conn, {"12345"}, 10) == []


def test_backfill_refetches_completed_activity_and_resumes(tmp_path):
    conn, api = _seeded()
    api.get_activity_details.reset_mock()
    state = tmp_path / "done.json"
    r = run_backfill(conn, api, state, limit=5, _sleep_fn=_NOSLEEP)
    assert r.synced_count == 1 and api.get_activity_details.call_count == 1
    r2 = run_backfill(conn, api, state, limit=5, _sleep_fn=_NOSLEEP)
    assert r2.total_items == 0 and api.get_activity_details.call_count == 1


def test_backfill_stops_on_rate_limit(tmp_path):
    conn, api = _seeded()
    for fn in (api.get_activity, api.get_activity_splits, api.get_activity_details,
               api.get_activity_hr_in_timezones, api.get_activity_weather):
        fn.side_effect = Exception("429 Too Many Requests")
    r = run_backfill(conn, api, tmp_path / "d.json", limit=5, _sleep_fn=_NOSLEEP)
    assert r.status == "partial" and r.http_status == 429 and r.synced_count == 0
