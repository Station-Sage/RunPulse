"""R3 — 플랜 주간 개요(PLN-1/5/7) 서비스·API."""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

import pytest

from src.db_setup import create_tables, migrate_db
from src.services import plan_overview_service as pos
from src.services import plan_template_service as pts
from src.services.plan_service import CUMULATIVE_BASIS, WEEK_BASIS

TODAY = date.today()


@pytest.fixture
def conn(tmp_path):
    c = sqlite3.connect(str(tmp_path / "running.db"))
    create_tables(c)
    migrate_db(c)
    yield c
    c.close()


def _make(conn):
    return pts.create_plan_from_template(conn, 21.0975, (TODAY + timedelta(weeks=12)).isoformat(), 8,
                                         run_weekdays=[0, 2, 4, 6])


def test_unknown_goal_returns_none(conn):
    assert pos.get_plan_overview(conn, 999) is None


def test_totals_equal_planned_workouts_aggregate(conn):
    gid = _make(conn)
    out = pos.get_plan_overview(conn, gid)
    total = conn.execute("SELECT COALESCE(SUM(distance_km),0) FROM planned_workouts WHERE goal_id=? AND source='planner'"
                         " AND workout_type NOT IN ('rest','race')", (gid,)).fetchone()[0]
    assert out["weeks"] and abs(sum(w["planned_km"] for w in out["weeks"]) - total) < 0.2
    assert all(w["run_days"] <= 4 and w["run_days"] + w["rest_days"] <= 7 for w in out["weeks"])
    assert out["basis"] == WEEK_BASIS and all(w["phase"] for w in out["weeks"])


def test_partial_first_week_carries_start_date(conn):
    gid = pts.create_plan_from_template(conn, 21.0975, (TODAY + timedelta(weeks=6)).isoformat(), 12,
                                        run_weekdays=[0, 1, 2, 3, 4, 5, 6])
    first = pos.get_plan_overview(conn, gid)["weeks"][0]
    mn = conn.execute("SELECT MIN(date) FROM planned_workouts WHERE goal_id=?", (gid,)).fetchone()[0]
    assert (first["start_date"] == mn) == (mn > first["week_start"])


def test_future_weeks_have_no_actuals(conn):
    gid = _make(conn)
    last = pos.get_plan_overview(conn, gid)["weeks"][-1]
    assert last["actual_km"] is None and last["compliance_pct"] is None


def test_cumulative_basis_labels():
    assert CUMULATIVE_BASIS["scope"] == "cumulative" and "누적" in CUMULATIVE_BASIS["label"]
    assert CUMULATIVE_BASIS["tooltip"]


def test_rematch_goal_matches_past_activity(conn):
    gid = _make(conn)
    assert pts.rematch_goal(conn, gid, TODAY + timedelta(days=30)) is not None


def test_rematch_goal_swallows_errors(conn):
    from src.training import rematch as R
    assert R.rematch_goal(sqlite3.connect(":memory:"), 1) is None
