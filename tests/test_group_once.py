"""tests/test_group_once.py — activity 계산 그룹당 1회·그룹 입력 병합(21 design §7.3 C3, DECISIONS D10)."""
from __future__ import annotations

import sqlite3

from src.db_setup import create_tables, migrate_db
from src.metrics.base import CalcContext
from src.metrics.engine import compute_for_activities, prune_noncanonical_runpulse, run_activity_metrics


def _conn():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    migrate_db(c)
    return c


def _act(conn, source, gid="g1", **kw):
    d = {"source": source, "source_id": f"{source}-1", "matched_group_id": gid, "name": "Run",
         "activity_type": "running", "start_time": "2026-09-20 08:00:00", "distance_m": 10000,
         "duration_sec": 3000, "moving_time_sec": 3000, "avg_hr": 140, "max_hr": 160}
    d.update(kw)
    conn.execute(f"INSERT INTO activity_summaries ({', '.join(d)}) VALUES ({', '.join('?' * len(d))})",
                 list(d.values()))
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def _rp_scopes(conn):
    return {r[0] for r in conn.execute(
        "SELECT DISTINCT scope_id FROM metric_store WHERE scope_type='activity' AND provider LIKE 'runpulse%'")}


def test_copy_id_is_computed_on_canonical_only():
    conn = _conn()
    g = _act(conn, "garmin")
    i = _act(conn, "intervals")
    compute_for_activities(conn, [i, g])
    assert _rp_scopes(conn) == {str(g)}


def test_stale_copy_rows_pruned():
    conn = _conn()
    g = _act(conn, "garmin")
    i = _act(conn, "intervals")
    conn.execute("INSERT INTO metric_store (scope_type, scope_id, metric_name, category, provider, numeric_value,"
                 " is_primary) VALUES ('activity', ?, 'trimp', 'load', 'runpulse:formula_v1', 101, 1)", (str(i),))
    assert prune_noncanonical_runpulse(conn) == 1
    run_activity_metrics(conn, g)
    assert _rp_scopes(conn) == {str(g)}


def test_group_streams_and_metric_filled_from_sibling():
    conn = _conn()
    g = _act(conn, "garmin")
    i = _act(conn, "intervals")
    conn.executemany("INSERT INTO activity_streams (activity_id, source, elapsed_sec, distance_m, speed_ms, heart_rate)"
                     " VALUES (?, 'intervals', ?, ?, 3.0, 150)", [(i, t, t * 3.0) for t in range(3001)])
    conn.execute("INSERT INTO metric_store (scope_type, scope_id, metric_name, category, provider, numeric_value,"
                 " is_primary) VALUES ('activity', ?, 'hr_zone_2_sec', 'hr_zone', 'intervals', 1800, 1)", (str(i),))
    ctx = CalcContext(conn=conn, scope_type="activity", scope_id=str(g))
    assert len(ctx.get_group_streams()) == 3001
    assert ctx.get_group_metric("hr_zone_2_sec") == 1800
