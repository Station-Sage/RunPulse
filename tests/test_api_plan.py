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


# ── /coach/plan/<goal_id>/session/<date> ─────────────────────────────────────

@pytest.fixture
def app_with_session(tmp_path):
    from datetime import date as _date, timedelta
    db_file = tmp_path / "running.db"
    conn = sqlite3.connect(str(db_file))
    create_tables(conn)
    migrate_db(conn)
    goal_id = _seed_goal(conn)
    today = _date.today()
    week_start = today - timedelta(days=today.weekday())
    session_date = week_start.isoformat()
    _seed_workout(conn, session_date, "long")
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
        yield client, goal_id, session_date

    routes_plan.db_path = _orig


def test_get_session_detail_200(app_with_session):
    client, goal_id, session_date = app_with_session
    res = client.get(f"/api/v1/coach/plan/{goal_id}/session/{session_date}")
    assert res.status_code == 200
    body = res.get_json()
    data = body["data"]
    assert data["goal"]["id"] == goal_id
    assert data["workout"]["date"] == session_date
    assert "week_index" in data
    assert "adjustment" in data
    assert "note" in data


def test_get_session_detail_404_missing_date(app_with_session):
    client, goal_id, _ = app_with_session
    res = client.get(f"/api/v1/coach/plan/{goal_id}/session/1990-01-01")
    assert res.status_code == 404


def test_get_session_detail_404_invalid_goal(app_with_session):
    client, _, session_date = app_with_session
    res = client.get(f"/api/v1/coach/plan/9999/session/{session_date}")
    assert res.status_code == 404


# ── POST /coach/plan/session/<date>/note ─────────────────────────────────────

def test_post_session_note_200(app_with_session):
    client, _, session_date = app_with_session
    res = client.post(
        f"/api/v1/coach/plan/session/{session_date}/note",
        json={"note": "훈련 잘 됐다"}
    )
    assert res.status_code == 200
    body = res.get_json()
    assert body["data"]["note"] == "훈련 잘 됐다"


def test_post_session_note_400_empty_note(app_with_session):
    client, _, session_date = app_with_session
    res = client.post(
        f"/api/v1/coach/plan/session/{session_date}/note",
        json={"note": "  "}
    )
    assert res.status_code == 400
    assert res.get_json()["error"]["code"] == "BAD_REQUEST"


def test_post_session_note_400_missing_note(app_with_session):
    client, _, session_date = app_with_session
    res = client.post(
        f"/api/v1/coach/plan/session/{session_date}/note",
        json={}
    )
    assert res.status_code == 400


# ── GET /coach/plan/adaptation ───────────────────────────────────────────────

def test_get_plan_adaptation_empty(mini_app):
    """데이터 없으면 200 + acwr/hrv/fatigue_avg 모두 None."""
    client, _ = mini_app
    res = client.get("/api/v1/coach/plan/adaptation")
    assert res.status_code == 200
    body = res.get_json()
    adaptation = body["data"]["adaptation"]
    assert adaptation["acwr"] is None
    assert adaptation["hrv"] is None
    assert adaptation["fatigue_avg"] is None


def test_get_plan_adaptation_with_acwr(mini_app):
    """acwr 행 삽입 후 GET → zone == '적정'(값 1.12)."""
    client, db_file = mini_app
    conn = sqlite3.connect(str(db_file))
    today = date.today().isoformat()
    conn.execute(
        "INSERT INTO metric_store (scope_type, scope_id, metric_name, provider, numeric_value, is_primary)"
        " VALUES ('daily', ?, 'acwr', 'runpulse', 1.12, 1)",
        (today,),
    )
    conn.commit()
    conn.close()

    res = client.get("/api/v1/coach/plan/adaptation")
    assert res.status_code == 200
    body = res.get_json()
    adaptation = body["data"]["adaptation"]
    assert adaptation["acwr"] is not None
    assert adaptation["acwr"]["zone"] == "적정"
