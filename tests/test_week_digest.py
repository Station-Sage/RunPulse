"""week_digest / 월간 프롬프트 W 블록 테스트 (U17g)."""
import datetime
import sqlite3

from src.db_setup import create_tables
from src.services._narrative import build_narrative_prompt
from src.services.week_digest import digest_prompt_lines, week_digest, weeks_overlapping


def _conn():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    return c


def test_weeks_overlapping_monday_start():
    w = weeks_overlapping("2026-03-01", "2026-03-31")
    assert w[0] == "2026-02-23" and w[-1] == "2026-03-30" and len(w) == 6


def test_empty_week_has_none_values():
    d = week_digest(_conn(), "2025-01-06")
    assert d["run_count"] == 0 and d["distance_km"] is None and d["flags"] == []
    assert d["partial"] is False and d["week_end"] == "2025-01-12"


def test_week_with_run_and_plan():
    c = _conn()
    c.execute("INSERT INTO activity_summaries (source, source_id, activity_type, start_time, distance_m)"
              " VALUES ('garmin','a1','running','2025-01-07T07:00:00',20000)")
    c.execute("INSERT INTO planned_workouts (date, workout_type, distance_km, completed) VALUES ('2025-01-07','long',20,0)")
    d = week_digest(c, "2025-01-06")
    assert d["run_count"] == 1 and d["long_run_km"] == 20.0
    assert d["plan_total"] == 1 and "plan_missed" in d["flags"]


def test_in_progress_week_is_partial():
    mon = datetime.date.today() - datetime.timedelta(days=datetime.date.today().weekday())
    d = week_digest(_conn(), mon.isoformat())
    assert d["partial"] is True and "plan_missed" not in d["flags"]


def test_prompt_contains_week_block():
    weeks = [{"week_start": "2026-03-02", "run_count": 3, "distance_km": 40.0, "long_run_km": 28.0,
              "ctl_end": 50.0, "tsb_min": -12.0, "partial": False}]
    p = build_narrative_prompt("2026-03-31", 50.0, 45.0, 100.0, 10, None, None, weeks=weeks)
    assert "W1(2026-03-02~)" in p and "롱런 28.0km" in p and "W2 롱런 28km" in p
    assert "W1" not in build_narrative_prompt("2026-03-31", 50.0, 45.0, 100.0, 10, None, None)


def test_prompt_lines_empty_week():
    assert "러닝 없음" in digest_prompt_lines([{"week_start": "2026-03-02", "run_count": 0}])[0]
