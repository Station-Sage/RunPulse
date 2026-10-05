"""POST /api/v1/coach/plan 선택 입력(최근 주간·최장 km)과 준비도 경고(warnings) — DESIGN-U16-LONGRUN §5.2."""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

import pytest
from flask import Flask

from src.db_setup import create_tables, migrate_db


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


def test_post_plan_reported_load_saved_and_warnings(mini_app, monkeypatch):
    """선택 입력(최근 주간·최장 km)은 목표에 저장되고, 응답에 warnings 목록이 있다."""
    client, db_file = mini_app
    monkeypatch.setenv("PLAN_RULES_V2_ENABLED", "1")
    res = client.post("/api/v1/coach/plan", json={
        "distance_km": 42.195, "weeks": 8, "race_date": (date.today() + timedelta(weeks=8)).isoformat(),
        "recent_weekly_km": 12, "recent_long_km": 8.5})
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert len(data["warnings"]) == 1 and "풀마라톤 준비 볼륨" in data["warnings"][0]
    conn = sqlite3.connect(str(db_file))
    row = conn.execute("SELECT reported_weekly_km, reported_long_km FROM goals WHERE id=?",
                       (data["goal_id"],)).fetchone()
    conn.close()
    assert row == (12.0, 8.5)


@pytest.mark.parametrize("bad", [{"recent_weekly_km": "abc"}, {"recent_weekly_km": -1}, {"recent_long_km": 99}])
def test_post_plan_400_bad_reported_load(mini_app, bad):
    client, _ = mini_app
    res = client.post("/api/v1/coach/plan", json={"distance_km": 10.0, "weeks": 8, **bad})
    assert res.status_code == 400
