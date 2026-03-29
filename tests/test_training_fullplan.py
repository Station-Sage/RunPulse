"""E-1: 전체 훈련 일정 뷰 테스트."""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from pathlib import Path

import pytest
from flask import Flask

from src.db_setup import create_tables, migrate_db
from src.web.views_training_fullplan import fullplan_bp
from src.web.views_training_loaders import load_full_plan_weeks


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def app():
    flask_app = Flask(__name__)
    flask_app.config["TESTING"] = True
    flask_app.register_blueprint(fullplan_bp)
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def db_file(tmp_path) -> Path:
    path = tmp_path / "test_fullplan.db"
    today = date.today()
    week_start = today - timedelta(days=today.weekday())

    with sqlite3.connect(str(path)) as conn:
        create_tables(conn)
        migrate_db(conn)
        # 활성 목표
        conn.execute(
            """INSERT INTO goals (name, distance_km, race_date, status)
               VALUES ('테스트 목표', 42.195, ?, 'active')""",
            ((today + timedelta(weeks=8)).isoformat(),),
        )
        # 2주치 워크아웃
        for offset in range(14):
            d = week_start + timedelta(days=offset)
            wtype = "rest" if d.weekday() == 6 else "easy"
            conn.execute(
                """INSERT INTO planned_workouts
                   (date, workout_type, distance_km, source)
                   VALUES (?, ?, ?, 'manual')""",
                (d.isoformat(), wtype, 10.0 if wtype != "rest" else None),
            )
        # 첫날 완료 처리
        conn.execute(
            "UPDATE planned_workouts SET completed=1 WHERE date=? AND workout_type='easy'",
            (week_start.isoformat(),),
        )
        conn.commit()
    return path


def _set_db(monkeypatch, db_file: Path) -> None:
    monkeypatch.setattr("src.web.views_training_fullplan.db_path", lambda: db_file)


# ── load_full_plan_weeks 단위 테스트 ──────────────────────────────────────


class TestLoadFullPlanWeeks:
    def test_groups_by_week(self, db_file):
        goal = {"race_date": (date.today() + timedelta(weeks=8)).isoformat(),
                "distance_km": 42.195}
        with sqlite3.connect(str(db_file)) as conn:
            weeks = load_full_plan_weeks(conn, goal)
        assert len(weeks) == 2

    def test_current_week_flagged(self, db_file):
        with sqlite3.connect(str(db_file)) as conn:
            weeks = load_full_plan_weeks(conn, None)
        current = [w for w in weeks if w["is_current"]]
        assert len(current) == 1

    def test_total_km_calculated(self, db_file):
        with sqlite3.connect(str(db_file)) as conn:
            weeks = load_full_plan_weeks(conn, None)
        # 각 주 6일 easy @ 10km = 60km
        for w in weeks:
            assert w["total_km"] == pytest.approx(60.0)

    def test_completed_count(self, db_file):
        with sqlite3.connect(str(db_file)) as conn:
            weeks = load_full_plan_weeks(conn, None)
        current = next(w for w in weeks if w["is_current"])
        assert current["completed_count"] == 1

    def test_no_goal_uses_12_week_horizon(self, db_file):
        with sqlite3.connect(str(db_file)) as conn:
            weeks = load_full_plan_weeks(conn, None)
        assert len(weeks) >= 1


# ── /training/fullplan 라우트 테스트 ─────────────────────────────────────


class TestFullplanRoute:
    def test_returns_200(self, client, db_file, monkeypatch):
        _set_db(monkeypatch, db_file)
        resp = client.get("/training/fullplan")
        assert resp.status_code == 200

    def test_contains_week_cards(self, client, db_file, monkeypatch):
        _set_db(monkeypatch, db_file)
        resp = client.get("/training/fullplan")
        body = resp.data.decode()
        assert "Week 1" in body
        assert "Week 2" in body

    def test_current_week_open(self, client, db_file, monkeypatch):
        _set_db(monkeypatch, db_file)
        resp = client.get("/training/fullplan")
        body = resp.data.decode()
        assert "<details open" in body

    def test_no_db_graceful(self, client, monkeypatch):
        monkeypatch.setattr(
            "src.web.views_training_fullplan.db_path",
            lambda: Path("/nonexistent/db.sqlite"),
        )
        resp = client.get("/training/fullplan")
        assert resp.status_code == 200
        assert "데이터 수집" in resp.data.decode()

    def test_goal_info_shown(self, client, db_file, monkeypatch):
        _set_db(monkeypatch, db_file)
        resp = client.get("/training/fullplan")
        assert "테스트 목표" in resp.data.decode()

    def test_back_link(self, client, db_file, monkeypatch):
        _set_db(monkeypatch, db_file)
        resp = client.get("/training/fullplan")
        assert "/training" in resp.data.decode()
