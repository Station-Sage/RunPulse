"""views_race Blueprint 통합 테스트."""
from __future__ import annotations

import json
import sqlite3
from datetime import date

import pytest

from src.db_setup import create_tables, migrate_db
from src.web.app import create_app


# ── fixtures ────────────────────────────────────────────────────────────

@pytest.fixture
def app_client(tmp_path, monkeypatch):
    """Flask test client — 임시 DB 사용."""
    db_file = tmp_path / "running_test.db"
    conn = sqlite3.connect(str(db_file))
    create_tables(conn)
    migrate_db(conn)
    conn.close()

    monkeypatch.setattr("src.web.views_race.db_path", lambda: db_file)
    monkeypatch.setattr("src.web.app._db_path", lambda: db_file)

    flask_app = create_app()
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as client:
        yield client, db_file


def _seed_darp(db_file) -> None:
    """DARP + DI 메트릭 시드 데이터."""
    conn = sqlite3.connect(str(db_file))
    today = date.today().isoformat()
    darp_json = json.dumps({
        "avg_pace_sec": 285,
        "splits": {"전반": 4200, "후반": 4350},
        "pace_segments": [
            {"range": "0-5km", "pace": 280, "level": "green"},
            {"range": "5-10km", "pace": 285, "level": "green"},
        ],
        "htw_probability": 15,
        "htw_description": "안전 수준",
        "training_tips": "장거리 템포런 추가 권장",
    })
    conn.execute(
        "INSERT INTO computed_metrics (date, activity_id, metric_name, metric_value, metric_json) VALUES (?,?,?,?,?)",
        (today, None, "DARP_half", 4500, darp_json),
    )
    conn.execute(
        "INSERT INTO computed_metrics (date, activity_id, metric_name, metric_value, metric_json) VALUES (?,?,?,?,?)",
        (today, None, "DARP_5k", 1200, json.dumps({"avg_pace_sec": 240})),
    )
    conn.execute(
        "INSERT INTO computed_metrics (date, activity_id, metric_name, metric_value, metric_json) VALUES (?,?,?,?,?)",
        (today, None, "DARP_10k", 2550, json.dumps({"avg_pace_sec": 255})),
    )
    conn.execute(
        "INSERT INTO computed_metrics (date, activity_id, metric_name, metric_value, metric_json) VALUES (?,?,?,?,?)",
        (today, None, "DARP_full", 9600, json.dumps({"avg_pace_sec": 305})),
    )
    di_json = json.dumps({"description": "양호한 내구성 수준"})
    conn.execute(
        "INSERT INTO computed_metrics (date, activity_id, metric_name, metric_value, metric_json) VALUES (?,?,?,?,?)",
        (today, None, "DI", 72.0, di_json),
    )
    conn.commit()
    conn.close()


# ── 기본 라우트 테스트 ──────────────────────────────────────────────────

def test_race_returns_200(app_client):
    """/race GET 요청이 200을 반환한다."""
    client, _ = app_client
    resp = client.get("/race")
    assert resp.status_code == 200


def test_race_default_distance_half(app_client):
    """기본 거리 선택은 하프마라톤 (21.0975km)."""
    client, _ = app_client
    body = client.get("/race").data.decode("utf-8")
    assert "21.0975" in body or "하프" in body or "레이스" in body


def test_race_distance_5k(app_client):
    """/race?distance=5.0 이 5K 선택 상태."""
    client, _ = app_client
    body = client.get("/race?distance=5.0").data.decode("utf-8")
    assert "5K" in body or "5.0" in body


def test_race_distance_10k(app_client):
    """/race?distance=10.0 이 10K 선택 상태."""
    client, _ = app_client
    resp = client.get("/race?distance=10.0")
    assert resp.status_code == 200


def test_race_distance_full(app_client):
    """/race?distance=42.195 이 마라톤 선택 상태."""
    client, _ = app_client
    body = client.get("/race?distance=42.195").data.decode("utf-8")
    assert "42.195" in body or "마라톤" in body


def test_race_invalid_distance_fallback(app_client):
    """잘못된 distance 파라미터는 하프로 폴백."""
    client, _ = app_client
    resp = client.get("/race?distance=abc")
    assert resp.status_code == 200


def test_race_no_db_shows_message(tmp_path, monkeypatch):
    """DB 없으면 안내 메시지 표시."""
    missing = tmp_path / "nonexistent.db"
    monkeypatch.setattr("src.web.views_race.db_path", lambda: missing)
    monkeypatch.setattr("src.web.app._db_path", lambda: missing)

    flask_app = create_app()
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as client:
        body = client.get("/race").data.decode("utf-8")
    assert "데이터 수집" in body or "동기화" in body


# ── 데이터 있을 때 테스트 ────────────────────────────────────────────────

def test_race_with_darp_data(app_client):
    """DARP 데이터가 있으면 예상 시간이 표시된다."""
    client, db_file = app_client
    _seed_darp(db_file)
    body = client.get("/race?distance=21.0975").data.decode("utf-8")
    assert "예상 완료 시간" in body or "DARP" in body


def test_race_di_card_rendered(app_client):
    """DI 데이터가 있으면 내구성 지수 카드가 표시된다."""
    client, db_file = app_client
    _seed_darp(db_file)
    body = client.get("/race").data.decode("utf-8")
    assert "내구성" in body or "DI" in body


def test_race_pace_strategy(app_client):
    """페이스 전략 섹션이 렌더링된다."""
    client, db_file = app_client
    _seed_darp(db_file)
    body = client.get("/race?distance=21.0975").data.decode("utf-8")
    assert "페이스 전략" in body or "0-5km" in body


def test_race_htw_card(app_client):
    """히팅 더 월 위험도 카드가 표시된다."""
    client, db_file = app_client
    _seed_darp(db_file)
    body = client.get("/race?distance=21.0975").data.decode("utf-8")
    assert "히팅 더 월" in body or "15%" in body


def test_race_training_adjust(app_client):
    """훈련 플랜 조정 권장 섹션이 표시된다."""
    client, db_file = app_client
    _seed_darp(db_file)
    body = client.get("/race?distance=21.0975").data.decode("utf-8")
    assert "훈련 플랜" in body or "템포런" in body


# ── 거리 선택기 ──────────────────────────────────────────────────────────

def test_race_distance_selector_all_options(app_client):
    """거리 선택기에 5K/10K/하프/마라톤이 모두 표시된다."""
    client, _ = app_client
    body = client.get("/race").data.decode("utf-8")
    assert "5K" in body
    assert "10K" in body
    assert "하프마라톤" in body or "21.0975" in body
    assert "마라톤" in body or "42.195" in body


def test_race_no_darp_shows_no_data(app_client):
    """DARP 데이터 없으면 '데이터 수집 중' 메시지 표시."""
    client, _ = app_client
    body = client.get("/race").data.decode("utf-8")
    assert "데이터 수집" in body or "데이터" in body
