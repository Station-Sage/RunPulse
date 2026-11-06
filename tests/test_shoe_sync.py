"""V2-SHOES T3 — sync 보강: Strava gear 종류·Garmin gear 배선(실패해도 계속)·Strava CSV 신발·Intervals gear id."""
import sqlite3
from unittest.mock import MagicMock

from src.db_setup import create_tables
from src.import_export.strava_shoes import gear_key, import_strava_shoes, link_activity_gear
from src.sync.extractors.intervals_extractor import _gear_id
from src.sync.garmin_activity_sync import sync
from src.sync.garmin_api_extensions import sync_activity_gear
from src.sync.strava_athlete_sync import strava_gear_type
from tests.test_garmin_activity_sync import SAMPLE_ACTIVITY, _mock_api


def _conn():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    return c


def test_strava_gear_type_bike_prefix():
    assert strava_gear_type("b123") == "bike"
    assert strava_gear_type("g123") == "shoes"


def test_intervals_gear_object_key():
    assert _gear_id({"gear": {"id": "g1", "name": None}}) == "g1"
    assert _gear_id({"gear": {"id": 34377}}) == "34377"
    assert _gear_id({"gear_id": "g9"}) == "g9"
    assert _gear_id({"gear": None}) is None


def test_garmin_gear_saved_and_linked():
    c = _conn()
    c.execute("INSERT INTO activity_summaries (id, source, source_id, activity_type, start_time)"
              " VALUES (1, 'garmin', '55', 'running', '2026-05-01T07:00:00')")
    client = MagicMock()
    client.get_activity_gear.return_value = [
        {"gearPk": 77, "gearTypeName": "Bike", "displayName": "Bike"},
        {"gearPk": 88, "gearTypeName": "Shoes", "customMakeModel": "Peg 40", "gearMakeName": "Nike"},
    ]
    assert sync_activity_gear(c, client, 1, "55") == "88"
    assert c.execute("SELECT gear_id FROM activity_summaries").fetchone() == ("88",)
    rows = dict(c.execute("SELECT source_gear_id, gear_type FROM gear").fetchall())
    assert rows == {"77": "bike", "88": "shoes"}


def test_garmin_gear_failure_retries_once_and_sync_continues():
    c = _conn()
    api = _mock_api(activities=[SAMPLE_ACTIVITY])
    api.get_activity_gear.side_effect = RuntimeError("boom")
    res = sync(c, api, days=1, _sleep_fn=lambda s: None)
    assert res.synced_count == 1 and res.error_count == 0
    assert api.get_activity_gear.call_count == 2


def test_strava_export_shoes_import_idempotent(tmp_path):
    c = _conn()
    f = tmp_path / "shoes.csv"
    f.write_text("Shoe Name,Shoe Brand,Shoe Model,Shoe Default Sport Types\n"
                 "My Peg,Nike,Pegasus 40,Run\n,ASICS,Kayano,\n,,,\n", encoding="utf-8")
    assert import_strava_shoes(c, f) == {"inserted": 2, "skipped": 1}
    assert import_strava_shoes(c, f) == {"inserted": 0, "skipped": 3}
    names = {r[0] for r in c.execute("SELECT source_gear_id FROM gear WHERE source='strava_export'")}
    assert names == {"mypeg", "asicskayano"}


def test_csv_activity_gear_link_only_when_empty():
    c = _conn()
    c.execute("INSERT INTO activity_summaries (id, source, source_id, activity_type, start_time)"
              " VALUES (1, 'strava', 's1', 'running', '2026-05-01T07:00:00')")
    c.execute("INSERT INTO activity_summaries (id, source, source_id, activity_type, start_time, gear_id)"
              " VALUES (2, 'strava', 's2', 'running', '2026-05-01T07:00:00', 'g1')")
    assert link_activity_gear(c, 1, "My Peg") is True
    assert link_activity_gear(c, 2, "My Peg") is False
    assert link_activity_gear(c, 1, None) is False
    assert gear_key("  My  Peg ") == "mypeg"
    assert [r[0] for r in c.execute("SELECT gear_id FROM activity_summaries ORDER BY id")] == ["mypeg", "g1"]
