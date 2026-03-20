"""views_activity Blueprint 유닛 테스트."""
from __future__ import annotations

import sqlite3
from datetime import date

import pytest

from src.db_setup import create_tables
from src.web.app import create_app


# ── fixtures ────────────────────────────────────────────────────────────

@pytest.fixture
def app_client(tmp_path, monkeypatch):
    """Flask test client — 임시 DB 사용."""
    db_file = tmp_path / "running_test.db"
    conn = sqlite3.connect(str(db_file))
    create_tables(conn)
    conn.close()

    # Blueprint는 helpers에서 직접 import하므로 각 모듈에서 패치해야 함
    monkeypatch.setattr("src.web.views_wellness.db_path", lambda: db_file)
    monkeypatch.setattr("src.web.views_activity.db_path", lambda: db_file)
    monkeypatch.setattr("src.web.app._db_path", lambda: db_file)

    flask_app = create_app()
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as client:
        yield client, db_file


def _insert_activity(conn: sqlite3.Connection, **kwargs) -> int:
    """테스트용 활동 삽입."""
    today = kwargs.get("start_time", date.today().isoformat() + "T06:00:00")
    cur = conn.execute(
        """
        INSERT INTO activity_summaries
        (source, source_id, activity_type, start_time,
         distance_km, duration_sec, avg_pace_sec_km, avg_hr, max_hr)
        VALUES ('garmin', ?, 'running', ?, ?, ?, ?, ?, ?)
        """,
        (
            f"garmin-{today}",
            today,
            kwargs.get("distance_km", 10.0),
            kwargs.get("duration_sec", 3000),
            kwargs.get("avg_pace_sec_km", 300),
            kwargs.get("avg_hr", 150),
            kwargs.get("max_hr", 175),
        ),
    )
    conn.commit()
    return cur.lastrowid


def _insert_daily_detail(conn: sqlite3.Connection, d: str, metric: str, value: float):
    conn.execute(
        "INSERT INTO daily_detail_metrics (date, source, metric_name, metric_value) "
        "VALUES (?, 'garmin', ?, ?)",
        (d, metric, value),
    )
    conn.commit()


# ── 라우트 테스트 ────────────────────────────────────────────────────────

class TestActivityDeepRoute:
    def test_no_db_returns_200(self, tmp_path, monkeypatch):
        """DB 없어도 200 반환."""
        missing = tmp_path / "nonexistent.db"
        monkeypatch.setattr("src.web.views_wellness.db_path", lambda: missing)
        monkeypatch.setattr("src.web.views_activity.db_path", lambda: missing)
        monkeypatch.setattr("src.web.app._db_path", lambda: missing)
        flask_app = create_app()
        flask_app.config["TESTING"] = True
        with flask_app.test_client() as client:
            resp = client.get("/activity/deep")
        assert resp.status_code == 200
        assert "running.db" in resp.data.decode()

    def test_no_activity(self, app_client):
        """활동 없을 때 graceful 표시."""
        client, _ = app_client
        resp = client.get("/activity/deep")
        assert resp.status_code == 200
        assert "활동" in resp.data.decode()

    def test_invalid_id(self, app_client):
        """잘못된 id 파라미터 처리."""
        client, _ = app_client
        resp = client.get("/activity/deep?id=abc")
        assert resp.status_code == 200
        assert "잘못된" in resp.data.decode()

    def test_activity_by_id(self, app_client):
        """id로 활동 조회 — 기본 정보 카드 표시."""
        client, db_file = app_client
        conn = sqlite3.connect(str(db_file))
        act_id = _insert_activity(conn, distance_km=12.5, avg_hr=155)
        conn.close()

        resp = client.get(f"/activity/deep?id={act_id}")
        assert resp.status_code == 200
        text = resp.data.decode()
        assert "활동 요약" in text
        assert "12.5" in text      # distance
        assert "155" in text       # avg_hr

    def test_garmin_daily_detail_shown(self, app_client):
        """garmin_daily_detail 카드 표시 확인."""
        client, db_file = app_client
        today = date.today().isoformat()
        with sqlite3.connect(str(db_file)) as conn:
            _insert_activity(conn, start_time=today + "T07:00:00")
            _insert_daily_detail(conn, today, "training_readiness_score", 65)
            _insert_daily_detail(conn, today, "overnight_hrv_avg", 52.3)
            _insert_daily_detail(conn, today, "sleep_stage_deep_sec", 4800)
            _insert_daily_detail(conn, today, "sleep_stage_rem_sec", 5400)
            _insert_daily_detail(conn, today, "spo2_avg", 96.8)
            _insert_daily_detail(conn, today, "body_battery_delta", -15)

        # 날짜 파라미터로 조회 (오늘 날짜의 최신 활동)
        resp = client.get(f"/activity/deep?date={today}")
        assert resp.status_code == 200
        text = resp.data.decode()

        assert "Garmin 일별 상세 지표" in text
        assert "65" in text        # training_readiness_score
        assert "52.3" in text      # overnight_hrv_avg
        assert "딥 슬립" in text
        assert "1h 20m" in text   # 4800s = 1h 20m (fmt_min 결과)
        assert "1h 30m" in text   # 5400s = 1h 30m (fmt_min 결과)
        assert "96.8" in text      # spo2_avg
        assert "-15" in text       # body_battery_delta

    def test_no_garmin_detail_shows_fallback(self, app_client):
        """daily_detail 없을 때 graceful fallback."""
        client, db_file = app_client
        conn = sqlite3.connect(str(db_file))
        act_id = _insert_activity(conn)
        conn.close()

        resp = client.get(f"/activity/deep?id={act_id}")
        assert resp.status_code == 200
        text = resp.data.decode()
        # 데이터 없음 메시지 또는 페이지 정상 반환
        assert "Garmin 일별 상세 지표" in text

    def test_date_param(self, app_client):
        """날짜 파라미터로 조회."""
        client, db_file = app_client
        today = date.today().isoformat()
        conn = sqlite3.connect(str(db_file))
        _insert_activity(conn, start_time=today + "T08:00:00", distance_km=8.0)
        conn.close()

        resp = client.get(f"/activity/deep?date={today}")
        assert resp.status_code == 200
        text = resp.data.decode()
        assert "활동 요약" in text
        assert "8.0" in text

    def test_query_form_present(self, app_client):
        """날짜/ID 조회 폼 포함 여부."""
        client, _ = app_client
        resp = client.get("/activity/deep")
        assert resp.status_code == 200
        assert "input" in resp.data.decode()

    def test_nav_shows_list_link(self, app_client):
        """네비 바에 목록 링크 포함."""
        client, db_file = app_client
        conn = sqlite3.connect(str(db_file))
        act_id = _insert_activity(conn)
        conn.close()
        resp = client.get(f"/activity/deep?id={act_id}")
        assert resp.status_code == 200
        assert "목록으로" in resp.data.decode()

    def test_nav_shows_prev_next(self, app_client):
        """이전/다음 활동 링크 표시."""
        client, db_file = app_client
        with sqlite3.connect(str(db_file)) as conn:
            id1 = _insert_activity(conn, start_time="2026-03-19T06:00:00")
            id2 = _insert_activity(conn, start_time="2026-03-20T06:00:00")
            id3 = _insert_activity(conn, start_time="2026-03-21T06:00:00")

        # 가운데 활동 조회 → 이전/다음 모두 있어야 함
        resp = client.get(f"/activity/deep?id={id2}")
        assert resp.status_code == 200
        text = resp.data.decode()
        assert "2026-03-19" in text   # 이전 날짜
        assert "2026-03-21" in text   # 다음 날짜

    def test_nav_no_prev_for_oldest(self, app_client):
        """가장 오래된 활동은 이전 없음."""
        client, db_file = app_client
        with sqlite3.connect(str(db_file)) as conn:
            id1 = _insert_activity(conn, start_time="2026-03-19T06:00:00")
            id2 = _insert_activity(conn, start_time="2026-03-21T06:00:00")

        resp = client.get(f"/activity/deep?id={id1}")
        text = resp.data.decode()
        assert "(없음)" in text   # 이전 없음 표시


# ── 홈 대시보드 테스트 ───────────────────────────────────────────────────

class TestHomeDashboard:
    def test_no_db_shows_setup(self, tmp_path, monkeypatch):
        """DB 없으면 설정 안내 표시."""
        missing = tmp_path / "nonexistent.db"
        monkeypatch.setattr("src.web.helpers.db_path", lambda: missing)
        monkeypatch.setattr("src.web.app._db_path", lambda: missing)
        flask_app = create_app()
        flask_app.config["TESTING"] = True
        with flask_app.test_client() as client:
            resp = client.get("/")
        assert resp.status_code == 200
        assert "db_setup" in resp.data.decode()

    def test_empty_db_shows_dashboard(self, app_client):
        """빈 DB여도 대시보드 반환."""
        client, _ = app_client
        resp = client.get("/")
        assert resp.status_code == 200
        text = resp.data.decode()
        assert "RunPulse" in text

    def test_with_activity_shows_recent(self, app_client):
        """활동 있을 때 최근 활동 표시."""
        client, db_file = app_client
        conn = sqlite3.connect(str(db_file))
        _insert_activity(conn, distance_km=15.0)
        conn.close()

        resp = client.get("/")
        assert resp.status_code == 200
        text = resp.data.decode()
        assert "최근 활동" in text
        assert "15.0" in text

    def test_recovery_card_link(self, app_client):
        """회복/웰니스 상세 링크 포함."""
        client, _ = app_client
        resp = client.get("/")
        assert resp.status_code == 200
        assert "/wellness" in resp.data.decode()
