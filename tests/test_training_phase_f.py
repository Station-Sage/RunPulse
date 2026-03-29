"""Phase F: Wizard edit 모드 + 목표 카드 인터랙션 테스트."""
from __future__ import annotations

import json
import sqlite3
from datetime import date, timedelta
from pathlib import Path

import pytest
from flask import Flask

from src.db_setup import create_tables, migrate_db
from src.web.views_training_wizard import wizard_bp, _goal_to_wizard_data, _parse_time, _fmt_time_hms, _fmt_pace_mmss
from src.web.views_training_wizard_render import render_step4
from src.web.views_training_cards import render_goal_card, _render_goal_card_actions
from src.web.views_training_crud import training_crud_bp


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def db_file(tmp_path) -> Path:
    path = tmp_path / "test_phasef.db"
    today = date.today()
    with sqlite3.connect(str(path)) as conn:
        create_tables(conn)
        migrate_db(conn)
        conn.execute(
            "INSERT INTO goals (name, race_date, distance_km, target_time_sec,"
            " target_pace_sec_km, status) VALUES (?,?,?,?,?,'active')",
            ("서울마라톤", str(today + timedelta(weeks=12)), 42.195, 14400, 343),
        )
        conn.execute(
            "INSERT INTO planned_workouts (date, workout_type, distance_km, source)"
            " VALUES (?,?,?,'manual')",
            (today.isoformat(), "easy", 10.0),
        )
        conn.commit()
    return path


@pytest.fixture
def app(db_file, monkeypatch):
    flask_app = Flask(__name__)
    flask_app.config["TESTING"] = True
    flask_app.register_blueprint(wizard_bp)
    flask_app.register_blueprint(training_crud_bp)

    _mock = lambda: db_file  # noqa: E731
    monkeypatch.setattr("src.web.views_training_wizard.db_path", _mock)
    monkeypatch.setattr("src.web.views_training_crud.db_path", _mock)
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


# ── F-1: Wizard edit 모드 ─────────────────────────────────────────────────


def test_goal_to_wizard_data_standard():
    """표준 거리 → distance_label 올바르게 변환."""
    g = {
        "id": 1, "name": "테스트", "race_date": "2026-10-01",
        "distance_km": 42.195, "target_time_sec": 14400,
        "target_pace_sec_km": 343,
    }
    d = _goal_to_wizard_data(g)
    assert d["distance_label"] == "full"
    assert d["goal_name"] == "테스트"
    assert d["dist_km"] == 42.195
    assert d["time_sec"] == 14400
    assert d["race_date"] == "2026-10-01"


def test_goal_to_wizard_data_custom():
    """비표준 거리 → custom 라벨."""
    g = {
        "id": 2, "name": "울트라", "race_date": None,
        "distance_km": 50.0, "target_time_sec": None, "target_pace_sec_km": None,
    }
    d = _goal_to_wizard_data(g)
    assert d["distance_label"] == "custom"
    assert d["custom_km"] == "50.0"


def test_fmt_time_hms():
    assert _fmt_time_hms(3600) == "1:00:00"
    assert _fmt_time_hms(3661) == "1:01:01"
    assert _fmt_time_hms(None) == ""


def test_fmt_pace_mmss():
    assert _fmt_pace_mmss(343) == "5:43"
    assert _fmt_pace_mmss(None) == ""


def test_render_step4_edit_mode():
    """edit 모드일 때 '목표 수정 완료' 버튼 + 재생성 체크박스 포함."""
    data = {
        "_mode": "edit", "_goal_id": 1,
        "goal_name": "수정된 목표", "dist_km": 42.195,
        "race_date": "2026-10-01", "plan_weeks": 12,
        "time_sec": 14400, "pace_sec": 343,
    }
    html = render_step4(data, mode="edit")
    assert "목표 수정 완료" in html
    assert "재생성" in html
    assert "wiz-regen-cb" in html


def test_render_step4_create_mode():
    """create 모드일 때 '플랜 생성' 버튼, 재생성 체크박스 없음."""
    data = {
        "goal_name": "새 목표", "dist_km": 10.0,
        "race_date": "2026-10-01", "plan_weeks": 8,
    }
    html = render_step4(data, mode="create")
    assert "플랜 생성" in html
    assert "wiz-regen-cb" not in html


def test_wizard_edit_get(client, db_file):
    """GET /training/wizard?mode=edit&goal_id=1 — 200 + 목표명 포함."""
    with sqlite3.connect(str(db_file)) as conn:
        gid = conn.execute("SELECT id FROM goals LIMIT 1").fetchone()[0]

    resp = client.get(f"/training/wizard?mode=edit&goal_id={gid}")
    assert resp.status_code == 200
    assert "서울마라톤".encode() in resp.data


# ── F-2/3/4: 목표 카드 버튼 ──────────────────────────────────────────────


def test_render_goal_card_no_goal():
    """목표 없으면 '훈련 계획 시작하기' 링크."""
    html = render_goal_card(None)
    assert "훈련 계획 시작하기" in html


def test_render_goal_card_with_goal_no_workout():
    """목표 있고 오늘 워크아웃 없으면 ✏️ 버튼만, ✕/✓ 없음."""
    goal = {
        "id": 1, "name": "서울마라톤", "distance_km": 42.195,
        "race_date": str(date.today() + timedelta(weeks=10)),
        "target_time_sec": 14400, "target_pace_sec_km": 343,
    }
    html = render_goal_card(goal, utrs_val=None, today_workout=None)
    assert "목표 수정" in html
    assert "✓ 완료" not in html
    assert "✕ 건너뜀" not in html


def test_render_goal_card_with_today_workout():
    """오늘 워크아웃 있으면 ✓/✕ 버튼 + AJAX JS 포함."""
    goal = {
        "id": 1, "name": "테스트", "distance_km": 10.0,
        "race_date": str(date.today() + timedelta(days=30)),
        "target_time_sec": None, "target_pace_sec_km": None,
    }
    today_w = {"id": 99, "workout_type": "easy", "distance_km": 8.0, "completed": 0}
    html = render_goal_card(goal, today_workout=today_w)
    assert "✓ 완료" in html
    assert "✕ 건너뜀" in html
    assert "rpGoalConfirm(99)" in html
    assert "rpGoalSkip(99)" in html


def test_render_goal_card_already_completed():
    """이미 완료된 워크아웃이면 버튼 없이 완료 텍스트."""
    goal = {"id": 1, "name": "테스트", "distance_km": 10.0,
            "race_date": None, "target_time_sec": None, "target_pace_sec_km": None}
    today_w = {"id": 99, "workout_type": "easy", "distance_km": 8.0, "completed": 1}
    html = render_goal_card(goal, today_workout=today_w)
    assert "✓ 오늘" in html
    assert "rpGoalConfirm" not in html


def test_render_goal_card_skipped():
    """스킵된 워크아웃이면 건너뜀 텍스트."""
    goal = {"id": 1, "name": "테스트", "distance_km": 10.0,
            "race_date": None, "target_time_sec": None, "target_pace_sec_km": None}
    today_w = {"id": 99, "workout_type": "easy", "distance_km": 8.0, "completed": -1}
    html = render_goal_card(goal, today_workout=today_w)
    assert "건너뜀" in html
    assert "rpGoalSkip" not in html


# ── F-4: confirm JSON ─────────────────────────────────────────────────────


def test_workout_confirm_json(client, db_file):
    """POST /training/workout/<id>/confirm Accept:json → ok:True 반환."""
    with sqlite3.connect(str(db_file)) as conn:
        wid = conn.execute("SELECT id FROM planned_workouts LIMIT 1").fetchone()[0]

    resp = client.post(
        f"/training/workout/{wid}/confirm",
        headers={"Accept": "application/json"},
    )
    assert resp.status_code == 200
    d = json.loads(resp.data)
    assert d["ok"] is True
    assert "matched" in d
    assert "activity_summary" in d


def test_workout_match_check(client, db_file):
    """GET /training/workout/<id>/match-check → matched 필드 포함."""
    with sqlite3.connect(str(db_file)) as conn:
        wid = conn.execute("SELECT id FROM planned_workouts LIMIT 1").fetchone()[0]

    resp = client.get(f"/training/workout/{wid}/match-check")
    assert resp.status_code == 200
    d = json.loads(resp.data)
    assert "matched" in d


def test_workout_match_check_not_found(client):
    """존재하지 않는 id → 404."""
    resp = client.get("/training/workout/99999/match-check")
    assert resp.status_code == 404
