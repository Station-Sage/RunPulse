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


# ── /coach/plan/templates ────────────────────────────────────────────────────

def test_get_templates_400_no_distance(mini_app):
    """distance_km 없으면 400."""
    client, _ = mini_app
    res = client.get("/api/v1/coach/plan/templates")
    assert res.status_code == 400
    assert res.get_json()["error"]["code"] == "BAD_REQUEST"


def test_get_templates_200(mini_app):
    """distance_km 있으면 200 + 템플릿 리스트 반환."""
    client, _ = mini_app
    res = client.get("/api/v1/coach/plan/templates?distance_km=42.195&target_time_sec=14400")
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert isinstance(data, list)
    assert len(data) >= 1
    assert "weeks" in data[0]
    assert "label" in data[0]


# ── POST /coach/plan ─────────────────────────────────────────────────────────

def test_post_plan_400_missing_fields(mini_app):
    """distance_km 또는 weeks 없으면 400."""
    client, _ = mini_app
    res = client.post("/api/v1/coach/plan", json={"distance_km": 42.195})
    assert res.status_code == 400
    assert res.get_json()["error"]["code"] == "BAD_REQUEST"


def test_post_plan_201_creates_goal(mini_app):
    """정상 요청 시 200 + goal_id 반환."""
    client, _ = mini_app
    res = client.post("/api/v1/coach/plan", json={
        "distance_km": 10.0,
        "weeks": 8,
        "target_time_sec": 2700
    })
    assert res.status_code == 200
    body = res.get_json()
    assert "goal_id" in body["data"]
    assert isinstance(body["data"]["goal_id"], int)
