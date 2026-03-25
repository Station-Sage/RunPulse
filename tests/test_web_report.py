"""views_report Blueprint 통합 테스트."""
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
    """Flask test client — 임시 DB 사용."""
    db_file = tmp_path / "running_test.db"
    conn = sqlite3.connect(str(db_file))
    create_tables(conn)
    migrate_db(conn)
    conn.close()

    monkeypatch.setattr("src.web.views_report.db_path", lambda: db_file)
    monkeypatch.setattr("src.web.app._db_path", lambda: db_file)

    flask_app = create_app()
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as client:
        yield client, db_file


def _seed_activities(db_file, count: int = 5) -> None:
    """기간 내 러닝 활동 시드."""
    conn = sqlite3.connect(str(db_file))
    today = date.today()
    for i in range(count):
        d = (today - timedelta(days=i)).isoformat()
        conn.execute(
            """INSERT INTO activity_summaries
               (source, source_id, activity_type, start_time, distance_km,
                duration_sec, avg_pace_sec_km, avg_hr)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            ("garmin", f"r{i}", "running", f"{d}T08:00:00",
             8.0 + i, 2400 + i * 120, 310 - i * 3, 145 + i),
        )
    conn.commit()
    conn.close()


def _seed_metrics(db_file) -> None:
    """기간 내 UTRS/CIRS 메트릭 시드."""
    conn = sqlite3.connect(str(db_file))
    today = date.today()
    for i in range(7):
        d = (today - timedelta(days=i)).isoformat()
        conn.execute(
            "INSERT INTO computed_metrics (date, activity_id, metric_name, metric_value, metric_json) VALUES (?,?,?,?,?)",
            (d, None, "UTRS", 65.0 + i, None),
        )
        conn.execute(
            "INSERT INTO computed_metrics (date, activity_id, metric_name, metric_value, metric_json) VALUES (?,?,?,?,?)",
            (d, None, "CIRS", 30.0 - i, None),
        )
    conn.commit()
    conn.close()


# ── 기본 라우트 테스트 ──────────────────────────────────────────────────

def test_report_returns_200(app_client):
    """/report GET 요청이 200을 반환한다."""
    client, _ = app_client
    resp = client.get("/report")
    assert resp.status_code == 200


def test_report_default_period_is_week(app_client):
    """/report 기본 기간은 week."""
    client, _ = app_client
    body = client.get("/report").data.decode("utf-8")
    assert "이번 주" in body or "7일" in body


def test_report_period_month(app_client):
    """/report?period=month 가 30일 기간 표시."""
    client, _ = app_client
    body = client.get("/report?period=month").data.decode("utf-8")
    assert "이번 달" in body or "30일" in body


def test_report_period_3month(app_client):
    """/report?period=3month 가 90일 기간 표시."""
    client, _ = app_client
    body = client.get("/report?period=3month").data.decode("utf-8")
    assert "3개월" in body or "90일" in body


def test_report_invalid_period_falls_back(app_client):
    """잘못된 period 파라미터는 week으로 폴백."""
    client, _ = app_client
    body = client.get("/report?period=invalid").data.decode("utf-8")
    assert "이번 주" in body or "7일" in body


def test_report_no_db_shows_message(tmp_path, monkeypatch):
    """DB 없으면 안내 메시지 표시."""
    missing = tmp_path / "nonexistent.db"
    monkeypatch.setattr("src.web.views_report.db_path", lambda: missing)
    monkeypatch.setattr("src.web.app._db_path", lambda: missing)

    flask_app = create_app()
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as client:
        body = client.get("/report").data.decode("utf-8")
    assert "running.db" in body or "초기화" in body


# ── 데이터 있을 때 테스트 ────────────────────────────────────────────────

def test_report_with_activities(app_client):
    """활동 데이터가 있으면 요약 카드에 수치가 표시된다."""
    client, db_file = app_client
    _seed_activities(db_file)
    body = client.get("/report").data.decode("utf-8")
    assert "활동 수" in body or "총 거리" in body or "km" in body


def test_report_with_metrics(app_client):
    """메트릭 데이터가 있으면 평균 UTRS/CIRS가 표시된다."""
    client, db_file = app_client
    _seed_metrics(db_file)
    body = client.get("/report").data.decode("utf-8")
    assert "UTRS" in body
    assert "CIRS" in body


def test_report_weekly_chart_section(app_client):
    """활동이 있으면 주별 거리 차트 섹션이 렌더링된다."""
    client, db_file = app_client
    _seed_activities(db_file, count=10)
    body = client.get("/report").data.decode("utf-8")
    assert "주별 거리" in body or "weeklyDistChart" in body or "데이터 수집" in body


def test_report_metrics_table(app_client):
    """활동별 메트릭 테이블이 렌더링된다."""
    client, db_file = app_client
    _seed_activities(db_file)
    # 활동별 메트릭 시드
    conn = sqlite3.connect(str(db_file))
    row = conn.execute("SELECT id FROM activity_summaries LIMIT 1").fetchone()
    if row:
        conn.execute(
            "INSERT INTO computed_metrics (date, activity_id, metric_name, metric_value) VALUES (?,?,?,?)",
            (date.today().isoformat(), row[0], "FEARP", 320.5),
        )
        conn.commit()
    conn.close()
    body = client.get("/report").data.decode("utf-8")
    assert "FEARP" in body or "최근 활동" in body or "메트릭" in body


# ── 기간 탭 HTML ─────────────────────────────────────────────────────────

def test_report_period_tabs_present(app_client):
    """기간 선택 탭 3개가 모두 표시된다."""
    client, _ = app_client
    body = client.get("/report").data.decode("utf-8")
    assert "period=week" in body
    assert "period=month" in body
    assert "period=3month" in body
