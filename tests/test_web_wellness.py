"""views_wellness Blueprint 및 helpers 유닛 테스트."""
from __future__ import annotations

import sqlite3
from datetime import date

import pytest

from src.db_setup import create_tables
from src.web.app import create_app
from src.web.helpers import (
    fmt_min,
    fmt_duration,
    metric_row,
    readiness_badge,
    safe_str,
    score_badge,
)


# ── fixtures ────────────────────────────────────────────────────────────

@pytest.fixture
def mem_db():
    """인메모리 DB — 테이블 생성 후 반환."""
    conn = sqlite3.connect(":memory:")
    create_tables(conn)
    yield conn
    conn.close()


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


# ── helpers 유닛 테스트 ─────────────────────────────────────────────────

class TestFmtMin:
    def test_none(self):
        assert fmt_min(None) == "—"

    def test_zero(self):
        assert fmt_min(0) == "0분"

    def test_minutes(self):
        assert fmt_min(3600) == "1h 0m"

    def test_exact_minutes(self):
        result = fmt_min(90 * 60)  # 5400초 = 90분 = 1h 30m
        assert "1h" in result
        assert "30m" in result

    def test_small(self):
        assert "분" in fmt_min(120)  # 2분


class TestFmtDuration:
    def test_none(self):
        assert fmt_duration(None) == "—"

    def test_seconds_only(self):
        assert fmt_duration(45) == "45s"

    def test_minutes(self):
        result = fmt_duration(3600)
        assert "1h" in result

    def test_minutes_seconds(self):
        result = fmt_duration(125)
        assert "2m" in result
        assert "5s" in result


class TestMetricRow:
    def test_none_value(self):
        html = metric_row("레이블", None)
        assert "레이블" in html
        assert "—" in html

    def test_with_unit(self):
        html = metric_row("심박", 150, " bpm")
        assert "150 bpm" in html

    def test_xss_escaping(self):
        html = metric_row("<script>", "<b>val</b>")
        assert "<script>" not in html
        assert "&lt;" in html


class TestScoreBadge:
    def test_excellent(self):
        html = score_badge("excellent", 85)
        assert "grade-excellent" in html
        assert "85" in html
        assert "최상" in html

    def test_none_score(self):
        html = score_badge(None, None)
        assert "—" in html

    def test_poor(self):
        html = score_badge("poor", 20)
        assert "grade-poor" in html


class TestReadinessBadge:
    def test_none(self):
        html = readiness_badge(None)
        assert "—" in html

    def test_high(self):
        html = readiness_badge(80)
        assert "grade-excellent" in html
        assert "준비 완료" in html

    def test_low(self):
        html = readiness_badge(20)
        assert "grade-poor" in html
        assert "회복 필요" in html


class TestSafeStr:
    def test_none(self):
        assert safe_str(None) == "—"

    def test_value(self):
        assert safe_str(42) == "42"

    def test_custom_default(self):
        assert safe_str(None, "없음") == "없음"


# ── wellness 라우트 테스트 ───────────────────────────────────────────────

class TestWellnessRoute:
    def test_no_db_returns_200(self, tmp_path, monkeypatch):
        """DB 없어도 200 반환."""
        missing = tmp_path / "nonexistent.db"
        monkeypatch.setattr("src.web.views_wellness.db_path", lambda: missing)
        monkeypatch.setattr("src.web.views_activity.db_path", lambda: missing)
        monkeypatch.setattr("src.web.app._db_path", lambda: missing)
        flask_app = create_app()
        flask_app.config["TESTING"] = True
        with flask_app.test_client() as client:
            resp = client.get("/wellness")
        assert resp.status_code == 200
        assert "running.db" in resp.data.decode()

    def test_no_garmin_data(self, app_client):
        """Garmin 데이터 없을 때 graceful 표시."""
        client, _ = app_client
        resp = client.get("/wellness")
        assert resp.status_code == 200
        text = resp.data.decode()
        assert "회복" in text

    def test_date_param(self, app_client):
        """날짜 파라미터 처리."""
        client, _ = app_client
        resp = client.get("/wellness?date=2026-01-01")
        assert resp.status_code == 200
        assert "2026-01-01" in resp.data.decode()

    def test_with_wellness_data(self, app_client):
        """Garmin 웰니스 데이터가 있을 때 카드 표시."""
        client, db_file = app_client
        today = date.today().isoformat()

        with sqlite3.connect(str(db_file)) as conn:
            conn.execute(
                "INSERT INTO daily_wellness "
                "(date, source, body_battery, sleep_score, hrv_value, stress_avg, resting_hr) "
                "VALUES (?, 'garmin', 80, 75, 55, 30, 48)",
                (today,),
            )
            conn.execute(
                "INSERT INTO daily_detail_metrics (date, source, metric_name, metric_value) "
                "VALUES (?, 'garmin', 'training_readiness_score', 72)",
                (today,),
            )
            conn.execute(
                "INSERT INTO daily_detail_metrics (date, source, metric_name, metric_value) "
                "VALUES (?, 'garmin', 'sleep_stage_deep_sec', 5400)",
                (today,),
            )
            conn.execute(
                "INSERT INTO daily_detail_metrics (date, source, metric_name, metric_value) "
                "VALUES (?, 'garmin', 'overnight_hrv_avg', 58.2)",
                (today,),
            )
            conn.execute(
                "INSERT INTO daily_detail_metrics (date, source, metric_name, metric_value) "
                "VALUES (?, 'garmin', 'spo2_avg', 97.5)",
                (today,),
            )
            conn.commit()

        resp = client.get(f"/wellness?date={today}")
        assert resp.status_code == 200
        text = resp.data.decode()

        assert "훈련 준비도" in text
        assert "72" in text        # training readiness score
        assert "야간 HRV" in text
        assert "58.2" in text      # overnight_hrv_avg
        assert "SpO2" in text
        assert "97.5" in text      # spo2_avg
        assert "딥 슬립" in text
        assert "1h 30m" in text   # 5400초 = 1h 30m (fmt_min 결과)

    def test_trend_table_shown(self, app_client):
        """추세 테이블 섹션 포함 여부."""
        client, _ = app_client
        resp = client.get("/wellness")
        assert resp.status_code == 200
        assert "추세" in resp.data.decode()
