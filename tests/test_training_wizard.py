"""훈련 계획 Wizard 통합 테스트 (Phase C)."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest
from flask import Flask

from src.db_setup import create_tables, migrate_db
from src.web.views_training_wizard import wizard_bp, _parse_time, _dist_km, _collect_mask


# ── Flask test app fixture ───────────────────────────────────────────────


@pytest.fixture
def app():
    """wizard_bp가 등록된 테스트용 Flask 앱."""
    flask_app = Flask(__name__)
    flask_app.config["TESTING"] = True
    flask_app.register_blueprint(wizard_bp)
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def db_file(tmp_path):
    """마이그레이션된 임시 SQLite DB 파일 경로."""
    path = tmp_path / "test_wizard.db"
    with sqlite3.connect(str(path)) as conn:
        create_tables(conn)
        migrate_db(conn)
    return path


# ── 헬퍼 함수 단위 테스트 ────────────────────────────────────────────────


class TestParseTime:
    def test_hhmmss(self):
        assert _parse_time("1:50:00") == 6600

    def test_mmss(self):
        assert _parse_time("5:30") == 330

    def test_empty(self):
        assert _parse_time("") is None
        assert _parse_time(None) is None  # type: ignore

    def test_invalid(self):
        assert _parse_time("abc") is None


class TestDistKm:
    def test_known_labels(self):
        assert _dist_km("5k", "") == 5.0
        assert _dist_km("10k", "") == 10.0
        assert _dist_km("half", "") == pytest.approx(21.097)
        assert _dist_km("full", "") == pytest.approx(42.195)

    def test_custom(self):
        assert _dist_km("custom", "30") == 30.0
        assert _dist_km("custom", "0") == 1.0   # min clamp
        assert _dist_km("custom", "bad") == 10.0  # fallback

    def test_unknown_label(self):
        assert _dist_km("unknown", "") == 10.0


# ── GET /training/wizard ─────────────────────────────────────────────────


def test_wizard_page_returns_200(client):
    resp = client.get("/training/wizard")
    assert resp.status_code == 200


def test_wizard_page_contains_step1(client):
    resp = client.get("/training/wizard")
    body = resp.data.decode()
    assert "Step 1" in body
    assert "레이스 목표" in body
    assert "wizard-container" in body


# ── POST /training/wizard/step ── step1 → step2 ─────────────────────────


def test_wizard_step1_returns_step2(client):
    resp = client.post("/training/wizard/step", data={
        "step": "1",
        "goal_name": "테스트 하프",
        "distance_label": "half",
        "custom_km": "",
        "race_date": "2026-09-20",
        "target_time": "1:50:00",
        "target_pace": "",
    })
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data["step"] == 2
    assert "Step 2" in data["html"]
    assert "훈련 환경" in data["html"]


def test_wizard_step1_pace_only_computes_time(client):
    """페이스만 입력 시 time_sec 계산."""
    resp = client.post("/training/wizard/step", data={
        "step": "1",
        "goal_name": "10K 테스트",
        "distance_label": "10k",
        "custom_km": "",
        "race_date": "2026-10-01",
        "target_time": "",
        "target_pace": "5:00",  # 300초/km → 10km → 3000초
    })
    assert resp.status_code == 200
    d = json.loads(resp.data)
    assert d["step"] == 2


def test_wizard_step1_custom_distance(client):
    wizard_data = json.dumps({
        "goal_name": "커스텀", "distance_label": "custom",
        "custom_km": "30", "dist_km": 30.0,
        "race_date": "2026-12-01", "time_sec": 9000,
        "target_time": "2:30:00", "target_pace": "", "pace_sec": None,
    })
    resp = client.post("/training/wizard/step", data={
        "step": "1",
        "goal_name": "커스텀",
        "distance_label": "custom",
        "custom_km": "30",
        "race_date": "2026-12-01",
        "target_time": "2:30:00",
        "target_pace": "",
    })
    assert resp.status_code == 200
    d = json.loads(resp.data)
    assert d["step"] == 2


# ── step2 → step3 ───────────────────────────────────────────────────────


def test_wizard_step2_returns_step3(client):
    wizard_data = json.dumps({
        "goal_name": "하프마라톤", "distance_label": "half",
        "custom_km": "", "dist_km": 21.097,
        "race_date": "2026-09-20",
        "target_time": "1:50:00", "time_sec": 6600,
        "target_pace": "", "pace_sec": None,
    })
    resp = client.post("/training/wizard/step", data={
        "step": "2",
        "wizard_data": wizard_data,
        "plan_weeks": "14",
        "interval_rep_m": "1000",
    })
    assert resp.status_code == 200
    d = json.loads(resp.data)
    assert d["step"] == 3
    assert "Step 3" in d["html"]
    assert "상태 분석" in d["html"]


def test_wizard_step2_no_db_graceful(client, monkeypatch):
    """DB 없어도 step3 반환 (graceful)."""
    import src.web.views_training_wizard as wiz
    monkeypatch.setattr(wiz, "db_path", lambda: Path("/nonexistent/test.db"))

    wizard_data = json.dumps({
        "goal_name": "테스트", "distance_label": "5k",
        "dist_km": 5.0, "race_date": "2026-08-01",
        "time_sec": 1500, "target_time": "0:25:00",
        "target_pace": "", "pace_sec": None,
    })
    resp = client.post("/training/wizard/step", data={
        "step": "2",
        "wizard_data": wizard_data,
        "plan_weeks": "8",
        "interval_rep_m": "800",
    })
    assert resp.status_code == 200
    d = json.loads(resp.data)
    assert d["step"] == 3
    assert "동기화" in d["html"]  # 경고 메시지 포함


# ── step3 → step4 ───────────────────────────────────────────────────────


def test_wizard_step3_returns_step4(client):
    wizard_data = json.dumps({
        "goal_name": "하프", "distance_label": "half",
        "dist_km": 21.097, "race_date": "2026-09-20",
        "time_sec": 6600, "target_time": "1:50:00",
        "target_pace": "", "pace_sec": None,
        "plan_weeks": 14, "rest_mask": 0, "long_mask": 64,
        "interval_rep_m": 1000, "blocked": [],
        "current_vdot": 45.0,
    })
    resp = client.post("/training/wizard/step", data={
        "step": "3",
        "wizard_data": wizard_data,
    })
    assert resp.status_code == 200
    d = json.loads(resp.data)
    assert d["step"] == 4
    assert "Step 4" in d["html"]
    assert "플랜 확인" in d["html"]
    assert "플랜 생성" in d["html"]


# ── POST /training/wizard/complete ──────────────────────────────────────


def test_wizard_complete_no_db(client, monkeypatch):
    """DB 없으면 에러 메시지로 redirect."""
    import src.web.views_training_wizard as wiz
    monkeypatch.setattr(wiz, "db_path", lambda: Path("/nonexistent/test.db"))

    wizard_data = json.dumps({
        "goal_name": "테스트", "dist_km": 10.0,
        "race_date": "2026-10-01", "time_sec": 3600,
        "pace_sec": None, "plan_weeks": 10,
        "rest_mask": 0, "long_mask": 0,
        "interval_rep_m": 1000, "blocked": [],
    })
    resp = client.post("/training/wizard/complete", data={"wizard_data": wizard_data})
    assert resp.status_code == 302
    assert "msg=" in resp.headers["Location"]


def test_wizard_complete_saves_goal(client, db_file, monkeypatch):
    """complete → goals + user_training_prefs 저장 + 플랜 생성 후 redirect."""
    import src.web.views_training_wizard as wiz
    monkeypatch.setattr(wiz, "db_path", lambda: db_file)

    wizard_data = json.dumps({
        "goal_name": "서울 마라톤", "dist_km": 42.195,
        "distance_label": "full",
        "race_date": "2026-11-01", "time_sec": 14400,
        "pace_sec": 341, "plan_weeks": 18,
        "rest_mask": 1, "long_mask": 64,
        "interval_rep_m": 1000, "blocked": [],
        "current_vdot": 45.0,
    })
    resp = client.post("/training/wizard/complete", data={"wizard_data": wizard_data})
    assert resp.status_code == 302
    from urllib.parse import unquote
    assert "생성" in unquote(resp.headers["Location"])

    # DB에 목표 저장 확인
    with sqlite3.connect(str(db_file)) as conn:
        row = conn.execute("SELECT name, distance_km FROM goals WHERE name='서울 마라톤'").fetchone()
    assert row is not None
    assert row[1] == pytest.approx(42.195)


def test_wizard_complete_bad_data(client):
    """wizard_data 없으면 에러 redirect."""
    resp = client.post("/training/wizard/complete", data={})
    assert resp.status_code == 302
    assert "msg=" in resp.headers["Location"]
