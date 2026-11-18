import json
import sqlite3
from datetime import datetime, timedelta, timezone

from src.db_setup import create_tables
from src.sync.wellness_series_backfill import backfill_series


def _conn():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    return c


def _put(c, d, typ, payload):
    c.execute("INSERT INTO source_payloads (source, entity_type, entity_id, entity_date, payload, payload_hash) "
              "VALUES ('garmin', ?, ?, ?, ?, 'h')", (typ, d, d, json.dumps(payload)))


def test_backfill_fills_series_and_skips_old_and_bad():
    c = _conn()
    d = (datetime.now(timezone.utc).date() - timedelta(days=10)).isoformat()
    ms = int(datetime.fromisoformat(d + "T01:00:00+00:00").timestamp() * 1000)
    _put(c, d, "wellness_hrv", {"hrvReadings": [{"readingTimeGMT": d + "T01:00:00.0", "hrvValue": 55}]})
    _put(c, "2020-01-01", "wellness_hrv", {"hrvReadings": []})
    c.commit()
    st = backfill_series(c, 400)
    assert st["errors"] == 0 and st["days"] == 1
    n = c.execute("SELECT COUNT(*) FROM wellness_series WHERE date=? AND kind='hrv_5min'", (d,)).fetchone()[0]
    assert n == 1
    assert ms
