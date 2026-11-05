"""scripts/prune_stale_crs: 첫 활동일 이전 구버전 crs 행만 삭제."""
import sqlite3

from scripts.prune_stale_crs import prune_stale_crs
from src.db_setup import create_tables, migrate_db


def _db():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    migrate_db(c)
    c.execute("INSERT INTO activity_summaries (source, source_id, activity_type, start_time) VALUES ('garmin','1','running','2023-10-29T06:00:00')")
    rows = [("2023-10-28", "1.0"), ("2023-10-29", "1.0"), ("2023-10-28", "1.1")]
    for d, v in rows:
        c.execute("INSERT INTO metric_store (scope_type, scope_id, metric_name, provider, numeric_value, algorithm_version, confidence, is_primary) "
                  "VALUES ('daily', ?, 'crs', ?, 60, ?, 1.0, 1)", (d, "p" + v, v))
    return c


def test_dry_run_keeps_rows():
    c = _db()
    assert prune_stale_crs(c) == 1
    assert c.execute("SELECT COUNT(*) FROM metric_store").fetchone()[0] == 3


def test_apply_deletes_only_stale():
    c = _db()
    assert prune_stale_crs(c, apply=True) == 1
    left = {(r[0], r[1]) for r in c.execute("SELECT scope_id, algorithm_version FROM metric_store")}
    assert left == {("2023-10-29", "1.0"), ("2023-10-28", "1.1")}


def test_no_activities_deletes_nothing():
    c = _db()
    c.execute("DELETE FROM activity_summaries")
    assert prune_stale_crs(c, apply=True) == 0
