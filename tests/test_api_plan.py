"""tests/test_api_plan.py — GET /api/v1/coach/plan/* 라우트 테스트."""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

import pytest
from flask import Flask

from src.db_setup import create_tables, migrate_db
from src.training.goals import add_goal


def _seed_goal(conn) -> int:
    return add_goal(conn, "서울 마라톤", 42.195, race_date="2027-03-15",
                    target_time_sec=14400)


def _seed_workout(conn, goal_date: str, workout_type: str = "easy",
                  completed: int = 0):
    conn.execute(
        "INSERT INTO planned_workouts "
        "(date, workout_type, distance_km, completed, source) "
        "VALUES (?, ?, ?, ?, 'planner')",
        (goal_date, workout_type, 10.0, completed),
    )
    conn.commit()


@pytest.fixture
def mini_app(tmp_path):
    db_file = tmp_path / "running.db"
    conn = sqlite3.connect(str(db_file))
    create_tables(conn)
    migrate_db(conn)
    conn.close()

    import src.api.routes_plan as routes_plan
    _orig = routes_plan.db_path
    routes_plan.db_path = lambda: db_file

    app = Flask(__name__)
    app.config["TESTING"] = True
    from src.api import api_bp
    app.register_blueprint(api_bp)

    with app.test_client() as client:
        yield client, db_file

    routes_plan.db_path = _orig


@pytest.fixture
def app_with_goal(tmp_path):
    db_file = tmp_path / "running.db"
    conn = sqlite3.connect(str(db_file))
    create_tables(conn)
    migrate_db(conn)
    goal_id = _seed_goal(conn)
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    _seed_workout(conn, week_start.isoformat(), "easy", completed=0)
    _seed_workout(conn, (week_start + timedelta(1)).isoformat(), "long",
                  completed=1)
    conn.commit()
    conn.close()

    import src.api.routes_plan as routes_plan
    _orig = routes_plan.db_path
    routes_plan.db_path = lambda: db_file

    app = Flask(__name__)
    app.config["TESTING"] = True
    from src.api import api_bp
    app.register_blueprint(api_bp)

    with app.test_client() as client:
        yield client, goal_id

    routes_plan.db_path = _orig


# ── /coach/plan/active ───────────────────────────────────────────────────────

def test_get_active_plan_404_no_goal(mini_app):
    client, _ = mini_app
    res = client.get("/api/v1/coach/plan/active")
    assert res.status_code == 404
    body = res.get_json()
    assert body["error"]["code"] == "NOT_FOUND"


def test_get_active_plan_200(app_with_goal):
    client, goal_id = app_with_goal
    res = client.get("/api/v1/coach/plan/active")
    assert res.status_code == 200
    body = res.get_json()
    data = body["data"]
    assert data["goal"]["name"] == "서울 마라톤"
    assert "week_index" in data
    assert "workouts" in data
    assert isinstance(data["workouts"], list)
    assert "compliance_pct" in data


# ── /coach/plan/<goal_id> ────────────────────────────────────────────────────

def test_get_plan_by_id_200(app_with_goal):
    client, goal_id = app_with_goal
    res = client.get(f"/api/v1/coach/plan/{goal_id}")
    assert res.status_code == 200
    body = res.get_json()
    assert body["data"]["goal"]["id"] == goal_id


def test_get_plan_by_id_404(app_with_goal):
    client, _ = app_with_goal
    res = client.get("/api/v1/coach/plan/9999")
    assert res.status_code == 404
    body = res.get_json()
    assert body["error"]["code"] == "NOT_FOUND"


# ── /coach/plan/adjustment ───────────────────────────────────────────────────

def test_get_adjustment_200_no_plan(mini_app):
    """플랜 없으면 adjusted=False 반환."""
    client, _ = mini_app
    res = client.get("/api/v1/coach/plan/adjustment")
    assert res.status_code == 200
    body = res.get_json()
    assert body["data"]["adjusted"] is False


def test_get_adjustment_200_with_plan(app_with_goal):
    """플랜 있어도 항상 200."""
    client, _ = app_with_goal
    res = client.get("/api/v1/coach/plan/adjustment")
    assert res.status_code == 200
    body = res.get_json()
    assert "adjusted" in body["data"]
