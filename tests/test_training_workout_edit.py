"""Phase D: 워크아웃 편집 AJAX 라우트 테스트.

- PATCH /training/workout/<id>
- GET  /training/workout/<id>/interval-calc
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest
from flask import Flask

from src.db_setup import create_tables, migrate_db
from src.web.views_training_crud import training_crud_bp


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def app():
    flask_app = Flask(__name__)
    flask_app.config["TESTING"] = True
    flask_app.register_blueprint(training_crud_bp)
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def db_file(tmp_path) -> Path:
    path = tmp_path / "test_edit.db"
    with sqlite3.connect(str(path)) as conn:
        create_tables(conn)
        migrate_db(conn)
        conn.execute(
            """INSERT INTO planned_workouts
               (date, workout_type, distance_km, target_pace_min, target_pace_max, source)
               VALUES ('2026-04-01', 'easy', 10.0, 270, 300, 'manual')"""
        )
        conn.commit()
    return path


@pytest.fixture
def workout_id(db_file) -> int:
    with sqlite3.connect(str(db_file)) as conn:
        row = conn.execute(
            "SELECT id FROM planned_workouts ORDER BY id LIMIT 1"
        ).fetchone()
    return row[0]


def _set_db(monkeypatch, db_file: Path) -> None:
    """helpers.db_path()가 임시 DB를 반환하도록 패치."""
    monkeypatch.setattr(
        "src.web.views_training_crud.db_path",
        lambda: db_file,
    )


# ── PATCH /training/workout/<id> ────────────────────────────────────────────


class TestWorkoutPatch:
    def test_patch_type_and_distance(self, client, db_file, workout_id, monkeypatch):
        _set_db(monkeypatch, db_file)
        resp = client.patch(
            f"/training/workout/{workout_id}",
            data=json.dumps({"workout_type": "tempo", "distance_km": 12.5}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True
        assert data["workout_type"] == "tempo"
        assert data["distance_km"] == pytest.approx(12.5)

    def test_patch_pace(self, client, db_file, workout_id, monkeypatch):
        _set_db(monkeypatch, db_file)
        resp = client.patch(
            f"/training/workout/{workout_id}",
            data=json.dumps({"target_pace_min": 255, "target_pace_max": 285}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True
        assert data["target_pace_min"] == 255
        assert data["target_pace_max"] == 285

    def test_patch_interval_saves_description(
        self, client, db_file, workout_id, monkeypatch
    ):
        _set_db(monkeypatch, db_file)
        resp = client.patch(
            f"/training/workout/{workout_id}",
            data=json.dumps(
                {
                    "workout_type": "interval",
                    "distance_km": 8.0,
                    "target_pace_min": 240,
                    "interval_rep_m": 1000,
                }
            ),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True
        # 처방 근거가 description에 저장됨
        assert data["description"] is not None
        assert "1000m" in data["description"]

    def test_patch_empty_body_returns_400(
        self, client, db_file, workout_id, monkeypatch
    ):
        _set_db(monkeypatch, db_file)
        resp = client.patch(
            f"/training/workout/{workout_id}",
            data=json.dumps({}),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_patch_nonexistent_db(self, client, monkeypatch):
        monkeypatch.setattr(
            "src.web.views_training_crud.db_path",
            lambda: Path("/nonexistent/db.sqlite"),
        )
        resp = client.patch(
            "/training/workout/1",
            data=json.dumps({"workout_type": "easy"}),
            content_type="application/json",
        )
        assert resp.status_code == 404

    def test_patch_persists_to_db(self, client, db_file, workout_id, monkeypatch):
        _set_db(monkeypatch, db_file)
        client.patch(
            f"/training/workout/{workout_id}",
            data=json.dumps({"workout_type": "long", "distance_km": 21.0}),
            content_type="application/json",
        )
        with sqlite3.connect(str(db_file)) as conn:
            row = conn.execute(
                "SELECT workout_type, distance_km FROM planned_workouts WHERE id=?",
                (workout_id,),
            ).fetchone()
        assert row[0] == "long"
        assert row[1] == pytest.approx(21.0)


# ── GET /training/workout/<id>/interval-calc ─────────────────────────────────


class TestIntervalCalc:
    def test_basic_1000m(self, client, db_file, workout_id, monkeypatch):
        _set_db(monkeypatch, db_file)
        resp = client.get(
            f"/training/workout/{workout_id}/interval-calc?rep_m=1000&pace=240"
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True
        assert data["rep_m"] == 1000
        assert data["sets"] >= 3
        assert data["rest_sec"] > 0
        assert "rationale" in data

    def test_200m_short_interval(self, client, db_file, workout_id, monkeypatch):
        _set_db(monkeypatch, db_file)
        resp = client.get(
            f"/training/workout/{workout_id}/interval-calc?rep_m=200&pace=210"
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True
        assert data["rep_m"] == 200

    def test_nonstandard_distance_warning(
        self, client, db_file, workout_id, monkeypatch
    ):
        _set_db(monkeypatch, db_file)
        resp = client.get(
            f"/training/workout/{workout_id}/interval-calc?rep_m=320&pace=235"
        )
        data = resp.get_json()
        assert data["ok"] is True
        assert data["warning"] is not None  # 비표준 거리 경고

    def test_default_params(self, client, db_file, workout_id, monkeypatch):
        """rep_m, pace 생략 시 기본값으로 계산."""
        _set_db(monkeypatch, db_file)
        resp = client.get(f"/training/workout/{workout_id}/interval-calc")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True
        assert data["rep_m"] == 1000
