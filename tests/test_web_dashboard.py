"""views_dashboard Blueprint 통합 테스트."""
from __future__ import annotations

import json
import sqlite3
from datetime import date, timedelta

import pytest

from src.db_setup import create_tables, migrate_db
from src.web.app import create_app


# ── fixtures ────────────────────────────────────────────────────────────

@pytest.fixture
def app_client(tmp_path, monkeypatch):
    """Flask test client — 임시 DB + 테이블/뷰 생성."""
    db_file = tmp_path / "running_test.db"
    conn = sqlite3.connect(str(db_file))
    create_tables(conn)
    migrate_db(conn)
    conn.close()

    monkeypatch.setattr("src.web.views_dashboard.db_path", lambda: db_file)
    monkeypatch.setattr("src.web.app._db_path", lambda: db_file)

    flask_app = create_app()
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as client:
        yield client, db_file


def _seed_activities(db_file, count: int = 3) -> None:
    """러닝 활동 시드 데이터 삽입."""
    conn = sqlite3.connect(str(db_file))
    today = date.today()
    for i in range(count):
        d = (today - timedelta(days=i)).isoformat()
        conn.execute(
            """INSERT INTO activity_summaries
               (source, source_id, activity_type, start_time, distance_km,
                duration_sec, avg_pace_sec_km, avg_hr)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            ("garmin", f"g{i}", "running", f"{d}T07:00:00",
             10.0 + i, 3000 + i * 60, 330 - i * 5, 150 + i),
        )
    conn.commit()
    conn.close()


def _seed_metrics(db_file) -> None:
    """computed_metrics + daily_fitness 시드 데이터."""
    conn = sqlite3.connect(str(db_file))
    today = date.today().isoformat()
    metrics = [
        (today, None, "UTRS", 72.5, json.dumps({"grade": "optimal", "sleep": 80, "hrv": 70, "tsb": 65, "rhr": 75, "consistency": 70})),
        (today, None, "CIRS", 28.0, json.dumps({"grade": "safe", "acwr": 0.9, "monotony": 1.1, "spike": 0, "asym": 0})),
        (today, None, "RMR", None, json.dumps({"axes": {"aerobic": 70, "threshold": 65, "endurance": 75, "efficiency": 60, "recovery": 80}})),
        (today, None, "ACWR", 1.05, None),
        (today, None, "LSI", 0.8, None),
        (today, None, "Monotony", 1.2, None),
    ]
    for d, act_id, name, val, mj in metrics:
        conn.execute(
            "INSERT INTO computed_metrics (date, activity_id, metric_name, metric_value, metric_json) VALUES (?,?,?,?,?)",
            (d, act_id, name, val, mj),
        )
    conn.execute(
        "INSERT INTO daily_fitness (date, source, ctl, atl, tsb) VALUES (?, ?, ?, ?, ?)",
        (today, "garmin", 45.0, 55.0, -10.0),
    )
    conn.commit()
    conn.close()


# ── 기본 라우트 테스트 ──────────────────────────────────────────────────

def test_dashboard_returns_200(app_client):
    """/dashboard GET 요청이 200을 반환한다."""
    client, _ = app_client
    resp = client.get("/dashboard")
    assert resp.status_code == 200


def test_dashboard_contains_key_sections(app_client):
    """대시보드에 핵심 섹션 키워드가 포함된다."""
    client, _ = app_client
    body = client.get("/dashboard").data.decode("utf-8")
    # 데이터 없어도 페이지 구조는 렌더링되어야 함
    assert "dashboard" in body.lower() or "대시보드" in body or "UTRS" in body


def test_dashboard_no_db_shows_init_message(tmp_path, monkeypatch):
    """DB 파일 없으면 초기화 안내 메시지 표시."""
    missing = tmp_path / "nonexistent.db"
    monkeypatch.setattr("src.web.views_dashboard.db_path", lambda: missing)
    monkeypatch.setattr("src.web.app._db_path", lambda: missing)

    flask_app = create_app()
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as client:
        body = client.get("/dashboard").data.decode("utf-8")
    assert "db_setup" in body.lower() or "초기화" in body or "동기화" in body


# ── 데이터 있을 때 테스트 ────────────────────────────────────────────────

def test_dashboard_with_activities(app_client):
    """활동 데이터가 있으면 활동 목록이 렌더링된다."""
    client, db_file = app_client
    _seed_activities(db_file)
    body = client.get("/dashboard").data.decode("utf-8")
    assert "10.0" in body or "km" in body


def test_dashboard_with_metrics(app_client):
    """메트릭 데이터가 있으면 UTRS/CIRS 카드가 표시된다."""
    client, db_file = app_client
    _seed_metrics(db_file)
    body = client.get("/dashboard").data.decode("utf-8")
    assert "UTRS" in body
    assert "CIRS" in body


def test_dashboard_with_full_data(app_client):
    """활동 + 메트릭 모두 있으면 전체 대시보드 렌더링."""
    client, db_file = app_client
    _seed_activities(db_file)
    _seed_metrics(db_file)
    body = client.get("/dashboard").data.decode("utf-8")
    assert "UTRS" in body
    assert "CIRS" in body
    assert resp_status(client.get("/dashboard")) == 200


def resp_status(resp) -> int:
    return resp.status_code


# ── PMC 차트 데이터 ──────────────────────────────────────────────────────

def test_dashboard_pmc_chart_rendered(app_client):
    """daily_fitness 데이터 있으면 PMC 차트 섹션이 렌더링된다."""
    client, db_file = app_client
    _seed_metrics(db_file)  # daily_fitness 포함
    body = client.get("/dashboard").data.decode("utf-8")
    # PMC 차트가 있거나, 데이터 수집 중 메시지라도 있어야 함
    assert "CTL" in body or "PMC" in body or "pmc" in body or "데이터 수집" in body


# ── RMR 레이더 카드 ──────────────────────────────────────────────────────

def test_dashboard_rmr_card(app_client):
    """RMR 메트릭이 있으면 러너 성숙도 레이더가 표시된다."""
    client, db_file = app_client
    _seed_metrics(db_file)
    body = client.get("/dashboard").data.decode("utf-8")
    assert "RMR" in body or "성숙도" in body


# ── resync 배너 ──────────────────────────────────────────────────────────

# ── V2-9-7: /analyze/* 리다이렉트 ──────────────────────────────────────

def test_analyze_today_redirects_to_dashboard(app_client):
    """/analyze/today 가 /dashboard 로 리다이렉트."""
    client, _ = app_client
    resp = client.get("/analyze/today")
    assert resp.status_code == 302
    assert "/dashboard" in resp.headers["Location"]


def test_analyze_full_redirects_to_report(app_client):
    """/analyze/full 이 /report 로 리다이렉트."""
    client, _ = app_client
    resp = client.get("/analyze/full")
    assert resp.status_code == 302
    assert "/report" in resp.headers["Location"]


def test_analyze_race_redirects_to_race(app_client):
    """/analyze/race 가 /race 로 리다이렉트."""
    client, _ = app_client
    resp = client.get("/analyze/race")
    assert resp.status_code == 302
    assert "/race" in resp.headers["Location"]


def test_dashboard_resync_banner(app_client):
    """needs_resync 플래그 설정 시 배너가 표시된다."""
    client, db_file = app_client
    conn = sqlite3.connect(str(db_file))
    conn.execute("CREATE TABLE IF NOT EXISTS schema_meta (id INTEGER PRIMARY KEY, needs_resync INTEGER DEFAULT 0)")
    conn.execute("INSERT OR REPLACE INTO schema_meta (id, needs_resync) VALUES (1, 1)")
    conn.commit()
    conn.close()
    body = client.get("/dashboard").data.decode("utf-8")
    assert "스키마" in body or "동기화" in body or "업데이트" in body
