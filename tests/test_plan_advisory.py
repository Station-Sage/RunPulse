"""plan_advisory — A1~A6 경고 계산·주 1회 발급·통증 제외."""
import json
import sqlite3
from datetime import date, timedelta

import pytest

from src.db_setup import create_tables, migrate_db
from src.services import plan_advisory

TODAY = date.today()


@pytest.fixture
def conn(tmp_path):
    c = sqlite3.connect(str(tmp_path / "running.db"))
    create_tables(c)
    migrate_db(c)
    yield c
    c.close()


def _adj(c, day, op="rest", wtype="easy", reasons=None, after="rest", decision="accepted"):
    c.execute("INSERT INTO planned_workouts(date,workout_type,distance_km,source) VALUES (?,?,8.0,'planner')",
              (day.isoformat(), wtype))
    wid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    c.execute("INSERT INTO plan_adjustments(goal_id,workout_id,date,source,op,before_json,after_json,reasons_json,"
              "rule_version,decision) VALUES (1,?,?,'user',?,?,?,?,'t',?)",
              (wid, day.isoformat(), op, json.dumps({"workout_type": wtype}), json.dumps({"workout_type": after}),
               json.dumps(reasons or []), decision))
    c.commit()
    return c.execute("SELECT last_insert_rowid()").fetchone()[0]


def _codes(items):
    return [a["code"] for a in items]


def test_empty_db_returns_nothing(conn):
    assert plan_advisory.compute(conn, TODAY.isoformat(), None) == []


def test_rest_streak_after_three_rest_days(conn):
    for i in range(2):
        _adj(conn, TODAY - timedelta(days=i + 1))
    assert "REST_STREAK" not in _codes(plan_advisory.compute(conn, TODAY.isoformat(), None))
    _adj(conn, TODAY)
    assert "REST_STREAK" in _codes(plan_advisory.compute(conn, TODAY.isoformat(), None))


def test_pain_rows_are_not_counted(conn):
    pain = [{"key": "pain", "level": "moderate", "sites": ["knee"]}]
    for i in range(3):
        _adj(conn, TODAY - timedelta(days=i), reasons=pain)
    assert plan_advisory.compute(conn, TODAY.isoformat(), None) == []


def test_week_drop_and_acwr_low(conn):
    delta = {"week_pct": -35.0, "acwr_after": 0.7}
    assert _codes(plan_advisory.compute(conn, TODAY.isoformat(), delta)) == ["WEEK_LOAD_DROP", "ACWR_LOW"]
    assert plan_advisory.compute(conn, TODAY.isoformat(), {"week_pct": -10.0, "acwr_after": 0.7}) == []


def test_q_dropped_twice(conn):
    _adj(conn, TODAY - timedelta(days=3), op="skip", wtype="tempo", after="rest")
    _adj(conn, TODAY, op="rest", wtype="interval")
    assert "Q_DROPPED_2" in _codes(plan_advisory.compute(conn, TODAY.isoformat(), None))


def test_issue_once_per_week_and_skips_pain(conn):
    delta = {"week_pct": -40.0, "acwr_after": 1.0}
    first = _adj(conn, TODAY, op="reduce")
    got = plan_advisory.issue(conn, first, TODAY.isoformat(), delta)
    assert _codes(got) == ["WEEK_LOAD_DROP"]
    stored = json.loads(conn.execute("SELECT reasons_json FROM plan_adjustments WHERE id=?", (first,)).fetchone()[0])
    assert {"key": "advisory", "code": "WEEK_LOAD_DROP"} in stored
    second = _adj(conn, TODAY, op="reduce")
    assert plan_advisory.issue(conn, second, TODAY.isoformat(), delta) == []
    painful = _adj(conn, TODAY, reasons=[{"key": "pain", "level": "mild", "sites": ["foot"]}])
    assert plan_advisory.issue(conn, painful, TODAY.isoformat(), {"week_pct": -50.0, "acwr_after": 0.5}) == []
