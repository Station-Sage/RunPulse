"""planner_config 조회 헬퍼의 as_of 시점 고정(U16a)."""
import sqlite3
from datetime import date

from src.training.planner_config import get_latest_fitness, get_marathon_shape_pct, get_vdot_adj


def _conn():
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE metric_store(metric_name TEXT, scope_type TEXT, scope_id TEXT, "
              "is_primary INT, numeric_value REAL)")
    for d, v in (("2026-01-01", 40.0), ("2026-02-01", 50.0)):
        for m, x in (("race_pred_vdot", v), ("marathon_shape", v), ("ctl", v), ("atl", v + 1), ("tsb", -1.0)):
            c.execute("INSERT INTO metric_store VALUES (?,?,?,?,?)", (m, "daily", d, 1, x))
    return c


def test_default_reads_latest():
    c = _conn()
    assert get_vdot_adj(c) == 50.0
    assert get_marathon_shape_pct(c) == 50.0
    assert get_latest_fitness(c)["ctl"] == 50.0


def test_as_of_cuts_future_values():
    c = _conn()
    d = date(2026, 1, 15)
    assert get_vdot_adj(c, d) == 40.0
    assert get_marathon_shape_pct(c, d) == 40.0
    assert get_latest_fitness(c, d) == {"ctl": 40.0, "atl": 41.0, "tsb": -1.0}


def test_as_of_before_data_is_empty():
    c = _conn()
    d = date(2025, 1, 1)
    assert get_vdot_adj(c, d) is None
    assert get_latest_fitness(c, d)["ctl"] == 0.0
