"""run_history 캐시: 집계 동일성·쓰기 후 무효화."""
import sqlite3
from datetime import date

from src.training import run_history
from src.training.planner_schedule import recent_avg_km, recent_load, recent_long_max


def _conn():
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE activity_summaries (id INTEGER PRIMARY KEY, source TEXT, matched_group_id TEXT,"
              " activity_type TEXT, start_time TEXT, distance_m REAL)")
    c.execute("CREATE VIEW v_canonical_activities AS SELECT *, 1 AS rn FROM activity_summaries")
    return c


def test_aggregates_and_invalidation():
    c = _conn()
    c.execute("INSERT INTO activity_summaries VALUES (1,'garmin',NULL,'running','2026-10-20T07:00:00',10000)")
    c.execute("INSERT INTO activity_summaries VALUES (2,'garmin',NULL,'cycling','2026-10-21T07:00:00',50000)")
    c.execute("INSERT INTO activity_summaries VALUES (3,'garmin',NULL,'running','2026-10-25T07:00:00',20000)")
    c.commit()
    as_of = date(2026, 11, 1)
    assert recent_load(c, as_of) == (7.5, 20.0)
    assert recent_long_max(c, as_of, 12) == 20.0
    assert recent_avg_km(c, as_of, 16) == round(30 / 16, 1)
    assert run_history.run_rows(c) is run_history.run_rows(c)
    c.execute("INSERT INTO activity_summaries VALUES (4,'garmin',NULL,'running','2026-10-30T07:00:00',30000)")
    assert recent_load(c, as_of) == (15.0, 30.0)
