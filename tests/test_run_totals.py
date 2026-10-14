"""run_totals / other_totals / other_line 테스트 (NRA N2)."""
import sqlite3

from src.db_setup import create_tables
from src.services.run_totals import other_line, other_totals, run_totals
from src.services.story_stats import _get_period_activity_stats
from src.services.week_digest import week_digest


def _conn():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    rows = [
        ("a1", "running", "2025-01-07T07:00:00", 10000, 3000),
        ("a2", "treadmill", "2025-01-08T07:00:00", 5000, 1800),
        ("a3", "swimming", "2025-01-09T07:00:00", 80000, 3600),
        ("a4", "cycling", "2025-01-09T09:00:00", 30000, 5400),
        ("a5", "strength", "2025-01-10T07:00:00", 0, 2400),
    ]
    for sid, t, st, d, du in rows:
        c.execute("INSERT INTO activity_summaries (source, source_id, activity_type, start_time,"
                  " distance_m, duration_sec) VALUES ('garmin',?,?,?,?,?)", (sid, t, st, d, du))
    return c


def test_run_totals_ignores_non_running():
    t = run_totals(_conn(), "2025-01-06", "2025-01-12")
    assert t == {"count": 2, "distance_km": 15.0, "longest_km": 10.0}


def test_run_totals_empty():
    assert run_totals(_conn(), "2024-01-01", "2024-01-07") == {
        "count": 0, "distance_km": 0.0, "longest_km": 0.0}


def test_other_totals_and_line():
    o = other_totals(_conn(), "2025-01-06", "2025-01-12")
    assert {x["family"] for x in o} == {"swimming", "cycling", "strength"}
    assert other_line(o).startswith("그 외 ") and "수영 1회" in other_line(o)
    assert other_line([]) == ""


def test_week_digest_and_story_stats_running_only():
    c = _conn()
    d = week_digest(c, "2025-01-06")
    assert d["run_count"] == 2 and d["distance_km"] == 15.0 and d["long_run_km"] == 10.0
    assert len(d["other"]) == 3
    s = _get_period_activity_stats(c, "2025-01-06", "2025-01-12")
    assert s["count"] == 2 and s["longest_run_km"] == 10.0
