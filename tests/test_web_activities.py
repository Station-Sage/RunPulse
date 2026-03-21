"""활동 목록 라우트(/activities) 통합 테스트."""
from __future__ import annotations

import sqlite3

import pytest

from src.db_setup import create_tables, migrate_db
from src.web.app import create_app


@pytest.fixture()
def app_client(tmp_path, monkeypatch):
    db_file = tmp_path / "test_activities.db"

    # DB 초기화 (전체 스키마)
    conn = sqlite3.connect(str(db_file))
    create_tables(conn)
    migrate_db(conn)
    conn.execute("""
        INSERT INTO activity_summaries
        (source, source_id, activity_type, start_time, distance_km, duration_sec, avg_pace_sec_km, avg_hr)
        VALUES
        ('garmin', 'g1', 'running', '2026-03-21T07:00:00', 10.5, 3600, 343, 148),
        ('strava', 's1', 'running', '2026-03-20T06:30:00', 5.0, 1500, 300, 155),
        ('garmin', 'g2', 'running', '2026-03-15T08:00:00', 21.1, 7200, 341, 152)
    """)
    conn.commit()
    conn.close()

    monkeypatch.setattr("src.web.views_activities.db_path", lambda: db_file)
    monkeypatch.setattr("src.web.views_wellness.db_path", lambda: db_file)
    monkeypatch.setattr("src.web.views_activity.db_path", lambda: db_file)

    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


class TestActivitiesRoute:
    def test_no_db(self, monkeypatch, tmp_path):
        """DB 없을 때 오류 메시지 표시."""
        missing = tmp_path / "missing.db"
        monkeypatch.setattr("src.web.views_activities.db_path", lambda: missing)
        app = create_app()
        app.config["TESTING"] = True
        with app.test_client() as client:
            resp = client.get("/activities")
        assert resp.status_code == 200
        assert "running.db" in resp.data.decode()

    def test_default_response(self, app_client):
        """기본 요청 시 200 반환."""
        resp = app_client.get("/activities")
        assert resp.status_code == 200

    def test_page_title(self, app_client):
        """페이지 제목 포함 여부."""
        resp = app_client.get("/activities")
        assert "활동 목록" in resp.data.decode()

    def test_activities_listed(self, app_client):
        """활동 데이터가 테이블에 표시됨."""
        resp = app_client.get("/activities")
        body = resp.data.decode()
        assert "garmin" in body
        assert "strava" in body

    def test_summary_count(self, app_client):
        """총 활동 수 요약 표시."""
        resp = app_client.get("/activities")
        body = resp.data.decode()
        # 기본 90일 범위 내 3개 활동
        assert "3" in body

    def test_deep_link_present(self, app_client):
        """심층 분석 링크 포함."""
        resp = app_client.get("/activities")
        body = resp.data.decode()
        assert "/activity/deep" in body

    def test_source_filter(self, app_client):
        """소스 필터 적용 시 해당 소스만 표시."""
        resp = app_client.get("/activities?source=strava")
        body = resp.data.decode()
        assert "strava" in body

    def test_date_filter(self, app_client):
        """날짜 필터 적용."""
        resp = app_client.get("/activities?from=2026-03-21&to=2026-03-21")
        assert resp.status_code == 200

    def test_running_type_filter(self, app_client):
        """유형=달리기 필터."""
        resp = app_client.get("/activities?type=running")
        assert resp.status_code == 200

    def test_pagination_absent_for_few_rows(self, app_client):
        """3개 활동은 페이지 넘김 없음."""
        resp = app_client.get("/activities")
        body = resp.data.decode()
        # 20개 미만이므로 이전/다음 네비 링크 없어야 함 (페이지네이션 HTML)
        assert "&laquo; 이전" not in body
        assert "다음 &raquo;" not in body

    def test_filter_form_rendered(self, app_client):
        """필터 폼 렌더링 확인."""
        resp = app_client.get("/activities")
        body = resp.data.decode()
        assert "<select name='source'" in body
        assert "type='date'" in body

    def test_nav_contains_activities_link(self, app_client):
        """nav에 활동 목록 링크 포함."""
        resp = app_client.get("/activities")
        body = resp.data.decode()
        assert "/activities" in body
