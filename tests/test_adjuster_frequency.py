"""adjuster_frequency: 주간 빈도·수락률 하락 롤백 판정."""
import sqlite3
from datetime import date, timedelta

from src.db_setup import create_tables
from src.services import adjuster_frequency as F
from src.services.user_settings_service import get_setting, set_setting

T = date(2026, 10, 14)


def _conn():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    return c


def _add(c, day, decision="proposed"):
    c.execute("INSERT INTO planned_workouts(date,workout_type) VALUES (?, 'easy')", (day,))
    wid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    c.execute("INSERT INTO plan_adjustments(workout_id,date,source,op,before_json,after_json,decision,rule_version)"
              " VALUES (?,?,'acwr','replace','{}','{}',?,'adjuster_v3')", (wid, day, decision))


def test_weekly_counts_and_rollback_needs_two_weeks():
    c = _conn()
    for i in range(4):
        _add(c, (T - timedelta(days=i)).isoformat(), "reverted")
    assert F.weekly_counts(c, T) == [0, 4]
    assert F.should_rollback(c, T) == []
    for i in range(7, 11):
        _add(c, (T - timedelta(days=i)).isoformat(), "reverted")
    assert F.should_rollback(c, T) == ["weekly_over"]


def test_acceptance_drop_and_min_sample():
    c = _conn()
    for i in range(10):
        _add(c, (T - timedelta(days=40 + i)).isoformat(), "accepted" if i < 8 else "reverted")
    assert not F.acceptance_drop(c)  # 표본 10 < 20
    for i in range(10):
        _add(c, (T - timedelta(days=i)).isoformat(), "accepted" if i < 3 else "reverted")
    assert F.acceptance_drop(c)  # 0.3 < 0.8 / 2


def test_acceptance_no_drop_when_prev_zero_or_stable():
    c = _conn()
    for i in range(10):
        _add(c, (T - timedelta(days=40 + i)).isoformat(), "reverted")
    for i in range(10):
        _add(c, (T - timedelta(days=i)).isoformat(), "reverted")
    assert not F.acceptance_drop(c)


def test_check_and_rollback_switches_version():
    c = _conn()
    assert F.check_and_rollback(c, T) == []
    set_setting(c, "adjuster_version", "v3")
    for i in list(range(0, 4)) + list(range(7, 11)):
        _add(c, (T - timedelta(days=i)).isoformat())
    assert F.check_and_rollback(c, T) == ["weekly_over"]
    assert get_setting(c, "adjuster_version") == "v2"


def test_backtest_run_summarizes_without_plan():
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location(
        "adjuster_backtest", Path(__file__).resolve().parent.parent / "scripts" / "adjuster_backtest.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    r = m.run(_conn(), T, days=5)
    assert r["v2"] == r["v3"] == 0 and r["weeks_over_3"] == 0
