"""get_plan_constraints 도구 — 선호·게이트 한계값 반환."""
import sqlite3

from src.ai.tool_exec_plan_constraints import _exec_get_plan_constraints
from src.ai.tools import _DISPATCH
from src.mcp_remote.policy import unclassified_tools


def test_registered_and_classified():
    assert "get_plan_constraints" in _DISPATCH
    assert not unclassified_tools()


def test_no_goal_defaults():
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE user_training_prefs(rest_weekdays_mask INT, workout_weekdays_mask INT,"
              " long_run_weekday_mask INT, blocked_dates TEXT, max_q_days INT)")
    c.execute("INSERT INTO user_training_prefs VALUES (0, 21, 16, '[\"2026-12-01\"]', 0)")
    c.execute("CREATE TABLE goals(id INTEGER PRIMARY KEY, name TEXT, race_date TEXT, distance_km REAL,"
              " target_time_sec INT, target_pace_sec_km REAL, status TEXT, created_at TEXT, plan_weeks INT, race_id INT)")
    c.execute("INSERT INTO goals VALUES (1,'m','2027-03-01',42.195,12000,0,'active','2026-01-01',16,NULL)")
    out = _exec_get_plan_constraints(c, {})
    assert out["prefs"]["workout_weekdays"] == ["월", "수", "금"]
    assert out["prefs"]["long_run_weekdays"] == ["금"]
    assert out["prefs"]["blocked_dates"] == ["2026-12-01"]
    assert out["goal"]["distance_label"] == "full"
    assert out["limits"]["long_abs_cap_km"] == 32.0
    assert out["limits"]["weekly_ramp_max"] == 0.10


def test_rows_to_weekplan_public():
    from src.training.plan_backtest import rows_to_weekplan
    rows = [{"date": "2026-12-01", "workout_type": "easy", "distance_km": 8.0},
            {"date": "2026-12-02", "workout_type": "rest"}]
    w = rows_to_weekplan(0, 5, rows)
    assert w.km == 8.0 and w.weeks_to_race == 5
