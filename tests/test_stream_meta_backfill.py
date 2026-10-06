"""U18e: 스트림 meta 백필."""
import json

from src.db_schema_v30 import ensure_v30
from src.sync.stream_meta_backfill import backfill_stream_meta
from tests.helpers_pred import mem_conn, seed_run

STREAMS = {"metricDescriptors": [{"key": "sumElapsedDuration", "metricsIndex": 0},
                                 {"key": "directHeartRate", "metricsIndex": 1}],
           "activityDetailMetrics": [{"metrics": [0.0, 120]}, {"metrics": [5.0, 125]}, {"metrics": [10.0, 130]}]}


def _setup():
    c = mem_conn()
    ensure_v30(c)
    aid = seed_run(c, sid="12345")
    c.execute("INSERT INTO source_payloads (source, entity_type, entity_id, payload) "
              "VALUES ('garmin','activity_streams','12345',?)", (json.dumps(STREAMS),))
    return c, aid


def test_backfill_garmin_writes_measured_meta():
    c, aid = _setup()
    backfill_stream_meta(c)
    r = c.execute("SELECT time_basis, stored_count FROM activity_stream_meta WHERE activity_id=?", (aid,)).fetchone()
    assert r == ("measured", 3)


def test_backfill_dry_run_writes_nothing_and_unknown_for_other_sources():
    c, aid = _setup()
    other = seed_run(c, sid="777")
    c.execute("INSERT INTO activity_streams (activity_id, source, elapsed_sec) VALUES (?, 'intervals', 4)", (other,))
    st = backfill_stream_meta(c, dry_run=True)
    assert other in st["targets"] and st["unknown"] == 1
    assert c.execute("SELECT count(*) FROM activity_stream_meta").fetchone()[0] == 0
    backfill_stream_meta(c)
    assert c.execute("SELECT time_basis FROM activity_stream_meta WHERE activity_id=?", (other,)).fetchone()[0] == "unknown"
