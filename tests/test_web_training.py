"""views_training Blueprint 통합 테스트.

6.7 Training Plan UI 재설계 (7열 그리드 캘린더, UTRS/CIRS 통합, AI 추천, 동기화 상태).
"""
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
    """Flask test client — 임시 DB + 테이블 생성."""
    db_file = tmp_path / "running_test.db"
    conn = sqlite3.connect(str(db_file))
    create_tables(conn)
    migrate_db(conn)
    conn.close()

    monkeypatch.setattr("src.web.views_training.db_path", lambda: db_file)
    monkeypatch.setattr("src.web.app._db_path", lambda: db_file)

    flask_app = create_app()
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as client:
        yield client, db_file


def _seed_workouts(db_file, week_offset: int = 0) -> None:
    """주간 운동 계획 시드 데이터."""
    conn = sqlite3.connect(str(db_file))
    today = date.today()
    week_start = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)
    types = ["easy", "interval", "easy", "tempo", "easy", "long", "rest"]
    dists = [5.0, 8.0, 5.0, 10.0, 6.0, 18.0, 0]
    for i, (wtype, dist) in enumerate(zip(types, dists)):
        d = (week_start + timedelta(days=i)).isoformat()
        completed = 1 if i < 2 else 0
        conn.execute(
            """INSERT INTO planned_workouts
               (date, workout_type, distance_km, target_pace_min, target_pace_max,
                target_hr_zone, description, rationale, completed, source)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (d, wtype, dist if dist else None,
             300 if wtype != "rest" else None,
             360 if wtype != "rest" else None,
             2 if wtype != "rest" else None,
             f"{wtype} 훈련", "Daniels method", completed, "planner"),
        )
    conn.commit()
    conn.close()


def _seed_goal(db_file) -> None:
    """활성 목표 시드 데이터."""
    conn = sqlite3.connect(str(db_file))
    race_date = (date.today() + timedelta(days=60)).isoformat()
    conn.execute(
        """INSERT INTO goals (name, race_date, distance_km, target_time_sec,
           target_pace_sec_km, status)
           VALUES (?, ?, ?, ?, ?, ?)""",
        ("서울마라톤 2026", race_date, 42.195, 10800, 256, "active"),
    )
    conn.commit()
    conn.close()


def _seed_metrics(db_file) -> None:
    """UTRS/CIRS 메트릭 시드 데이터."""
    conn = sqlite3.connect(str(db_file))
    today = date.today().isoformat()
    conn.execute(
        "INSERT INTO computed_metrics (date, activity_id, metric_name, metric_value, metric_json) "
        "VALUES (?, ?, ?, ?, ?)",
        (today, None, "UTRS", 75.0,
         json.dumps({"grade": "optimal", "sleep": 80, "hrv": 70})),
    )
    conn.execute(
        "INSERT INTO computed_metrics (date, activity_id, metric_name, metric_value, metric_json) "
        "VALUES (?, ?, ?, ?, ?)",
        (today, None, "CIRS", 35.0,
         json.dumps({"grade": "moderate", "acwr_risk": 0.3})),
    )
    conn.commit()
    conn.close()


def _seed_sync_jobs(db_file) -> None:
    """동기화 이력 시드 데이터."""
    conn = sqlite3.connect(str(db_file))
    for svc in ("garmin", "strava", "intervals"):
        conn.execute(
            "INSERT INTO sync_jobs "
            "(id, service, from_date, to_date, window_days, status, "
            " completed_days, total_days, synced_count, req_count, "
            " created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (f"sync-{svc}", svc, "2026-03-20", "2026-03-25", 5,
             "completed", 5, 5, 10, 10,
             "2026-03-25 10:30:00", "2026-03-25 10:30:00"),
        )
    conn.commit()
    conn.close()


# ── 기본 라우트 테스트 ─────────────────────────────────────────────────


class TestTrainingPage:
    """GET /training 기본 동작."""

    def test_empty_db_returns_200(self, app_client):
        client, _ = app_client
        resp = client.get("/training")
        assert resp.status_code == 200
        assert "훈련 계획" in resp.data.decode()

    def test_no_plan_shows_goal_prompt(self, app_client):
        client, _ = app_client
        resp = client.get("/training")
        html = resp.data.decode()
        assert "설정된 목표가 없습니다" in html

    def test_with_goal_shows_dday(self, app_client):
        client, db_file = app_client
        _seed_goal(db_file)
        resp = client.get("/training")
        html = resp.data.decode()
        assert "서울마라톤" in html
        assert "D-" in html

    def test_with_workouts_shows_calendar(self, app_client):
        client, db_file = app_client
        _seed_workouts(db_file)
        resp = client.get("/training")
        html = resp.data.decode()
        # 7열 그리드 확인
        assert "grid-template-columns:repeat(7" in html
        # 요일 헤더 확인
        assert "월" in html and "화" in html and "일" in html

    def test_with_workouts_shows_summary(self, app_client):
        client, db_file = app_client
        _seed_workouts(db_file)
        resp = client.get("/training")
        html = resp.data.decode()
        assert "이번 주 요약" in html
        assert "훈련 완료" in html
        assert "목표 km" in html

    def test_completed_workouts_count(self, app_client):
        client, db_file = app_client
        _seed_workouts(db_file)
        resp = client.get("/training")
        html = resp.data.decode()
        # 2/6 완료 (rest 제외)
        assert "2/6" in html


class TestWeekNavigation:
    """주 네비게이션 (?week= 파라미터)."""

    def test_default_week_is_current(self, app_client):
        client, db_file = app_client
        _seed_workouts(db_file, week_offset=0)
        resp = client.get("/training")
        html = resp.data.decode()
        today = date.today()
        assert str(today.day) in html

    def test_prev_week(self, app_client):
        client, db_file = app_client
        _seed_workouts(db_file, week_offset=-1)
        resp = client.get("/training?week=-1")
        html = resp.data.decode()
        assert "week=-2" in html  # 이전 주 네비 링크

    def test_next_week(self, app_client):
        client, db_file = app_client
        resp = client.get("/training?week=1")
        html = resp.data.decode()
        assert "week=2" in html  # 다음 주 네비 링크


class TestHeaderActions:
    """S1: 헤더 액션 버튼."""

    def test_generate_button_present(self, app_client):
        client, _ = app_client
        resp = client.get("/training")
        html = resp.data.decode()
        assert "플랜 생성" in html
        assert "/training/generate" in html

    def test_header_title_present(self, app_client):
        """훈련 계획 헤더 타이틀 항상 표시."""
        client, _ = app_client
        resp = client.get("/training")
        html = resp.data.decode()
        assert "훈련 계획" in html


class TestMetricsIntegration:
    """UTRS/CIRS 메트릭 표시."""

    def test_utrs_in_goal_card(self, app_client):
        client, db_file = app_client
        _seed_goal(db_file)
        _seed_metrics(db_file)
        resp = client.get("/training")
        html = resp.data.decode()
        assert "UTRS" in html
        assert "75" in html

    def test_utrs_in_weekly_summary(self, app_client):
        client, db_file = app_client
        _seed_workouts(db_file)
        _seed_metrics(db_file)
        resp = client.get("/training")
        html = resp.data.decode()
        assert "UTRS" in html


class TestAIRecommendation:
    """S6: AI 훈련 추천 카드."""

    def test_ai_card_with_metrics(self, app_client):
        client, db_file = app_client
        _seed_workouts(db_file)
        _seed_metrics(db_file)
        resp = client.get("/training")
        html = resp.data.decode()
        assert "AI 훈련 추천" in html
        assert "🤖" in html

    def test_no_ai_card_without_metrics(self, app_client):
        client, db_file = app_client
        _seed_workouts(db_file)
        resp = client.get("/training")
        html = resp.data.decode()
        assert "AI 훈련 추천" not in html


class TestSyncStatus:
    """S7: 동기화 상태."""

    def test_sync_status_shown(self, app_client):
        client, db_file = app_client
        _seed_sync_jobs(db_file)
        resp = client.get("/training")
        html = resp.data.decode()
        assert "데이터 연동" in html
        assert "Garmin Connect" in html

    def test_no_sync_no_section(self, app_client):
        client, _ = app_client
        resp = client.get("/training")
        html = resp.data.decode()
        assert "데이터 연동" not in html


class TestGenerateRoute:
    """POST /training/generate."""

    def test_generate_redirects(self, app_client):
        client, db_file = app_client
        _seed_goal(db_file)
        resp = client.post("/training/generate", follow_redirects=False)
        assert resp.status_code == 302
        assert "/training" in resp.headers.get("Location", "")

    def test_generate_without_db(self, app_client, monkeypatch):
        client, _ = app_client
        monkeypatch.setattr(
            "src.web.views_training.db_path",
            lambda: None,
        )
        resp = client.post("/training/generate", follow_redirects=False)
        assert resp.status_code == 302


# ── 카드 렌더러 단위 테스트 ────────────────────────────────────────────


class TestRenderCards:
    """views_training_cards 개별 렌더러."""

    def test_render_goal_card_empty(self):
        from src.web.views_training_cards import render_goal_card
        html = render_goal_card(None)
        assert "설정된 목표가 없습니다" in html

    def test_render_goal_card_with_data(self):
        from src.web.views_training_cards import render_goal_card
        goal = {
            "name": "테스트 레이스",
            "distance_km": 21.1,
            "race_date": (date.today() + timedelta(days=30)).isoformat(),
            "target_time_sec": 5400,
            "target_pace_sec_km": 256,
        }
        html = render_goal_card(goal, utrs_val=82.0)
        assert "테스트 레이스" in html
        assert "D-30" in html
        assert "UTRS 82" in html

    def test_render_weekly_summary_empty(self):
        from src.web.views_training_cards import render_weekly_summary
        assert render_weekly_summary([]) == ""

    def test_render_weekly_summary_with_data(self):
        from src.web.views_training_cards import render_weekly_summary
        workouts = [
            {"workout_type": "easy", "distance_km": 5.0, "completed": 1,
             "target_pace_min": 300, "target_pace_max": 360},
            {"workout_type": "tempo", "distance_km": 10.0, "completed": 0,
             "target_pace_min": 270, "target_pace_max": 290},
            {"workout_type": "rest", "distance_km": None, "completed": 0},
        ]
        html = render_weekly_summary(workouts, utrs_val=65.0)
        assert "이번 주 요약" in html
        assert "1/2" in html  # 1 completed / 2 non-rest
        assert "15.0" in html  # total km
        assert "UTRS" in html

    def test_render_adjustment_card_none(self):
        from src.web.views_training_cards import render_adjustment_card
        assert render_adjustment_card(None) == ""

    def test_render_adjustment_card_no_change(self):
        from src.web.views_training_cards import render_adjustment_card
        adj = {
            "adjusted": False,
            "fatigue_level": "low",
            "volume_boost": False,
            "wellness": {"body_battery": 75, "sleep_score": 85},
        }
        html = render_adjustment_card(adj)
        assert "계획대로 진행" in html
        assert "BB 75" in html

    def test_render_adjustment_card_adjusted(self):
        from src.web.views_training_cards import render_adjustment_card
        adj = {
            "adjusted": True,
            "original_type": "interval",
            "adjusted_type": "easy",
            "adjustment_reason": "피로도 높음: BB 20",
            "fatigue_level": "high",
            "wellness": {"body_battery": 20, "sleep_score": 40},
            "tsb": -20.0,
        }
        html = render_adjustment_card(adj)
        assert "컨디션 조정" in html
        assert "인터벌" in html
        assert "이지런" in html
        assert "TSB" in html

    def test_render_week_calendar(self):
        from src.web.views_training_cards import render_week_calendar
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        workouts = [
            {"date": (week_start + timedelta(days=i)).isoformat(),
             "workout_type": "easy", "distance_km": 5.0,
             "completed": 0, "target_pace_min": 300, "target_pace_max": 360}
            for i in range(7)
        ]
        html = render_week_calendar(workouts, week_start, 0)
        assert "repeat(7" in html
        assert "월" in html
        assert "일" in html

    def test_render_ai_recommendation_no_data(self):
        from src.web.views_training_cards import render_ai_recommendation
        assert render_ai_recommendation(None, None, {}, []) == ""

    def test_render_ai_recommendation_with_utrs(self):
        from src.web.views_training_cards import render_ai_recommendation
        html = render_ai_recommendation(80.0, None, {}, [])
        assert "AI 훈련 추천" in html
        assert "UTRS 80" in html
        assert "고강도" in html

    def test_render_ai_recommendation_low_utrs(self):
        from src.web.views_training_cards import render_ai_recommendation
        html = render_ai_recommendation(30.0, None, {}, [])
        assert "회복이 필요" in html

    def test_render_ai_recommendation_high_cirs(self):
        from src.web.views_training_cards import render_ai_recommendation
        html = render_ai_recommendation(
            60.0, 75.0, {"grade": "high"}, [])
        assert "부상 위험" in html

    def test_render_sync_status_empty(self):
        from src.web.views_training_cards import render_sync_status
        assert render_sync_status([]) == ""

    def test_render_sync_status_with_data(self):
        from src.web.views_training_cards import render_sync_status
        sync = [
            {"service": "garmin", "last_sync": "2026-03-25 10:30", "status": "completed"},
            {"service": "strava", "last_sync": "2026-03-24 08:00", "status": "completed"},
        ]
        html = render_sync_status(sync)
        assert "Garmin Connect" in html
        assert "Strava" in html
        assert "동기화 완료" in html

    def test_render_header_actions(self):
        from src.web.views_training_cards import render_header_actions
        html = render_header_actions(True)
        assert "재생성" in html
        html2 = render_header_actions(False)
        assert "플랜 생성" in html2


# ── 로더 단위 테스트 ───────────────────────────────────────────────────


class TestLoaders:
    """views_training_loaders 데이터 로드."""

    def test_load_workouts_current_week(self, app_client):
        _, db_file = app_client
        _seed_workouts(db_file)
        conn = sqlite3.connect(str(db_file))
        from src.web.views_training_loaders import load_workouts
        workouts, ws = load_workouts(conn, week_offset=0)
        conn.close()
        assert len(workouts) == 7
        assert ws.weekday() == 0  # 월요일

    def test_load_workouts_empty_week(self, app_client):
        _, db_file = app_client
        conn = sqlite3.connect(str(db_file))
        from src.web.views_training_loaders import load_workouts
        workouts, ws = load_workouts(conn, week_offset=5)
        conn.close()
        assert workouts == []

    def test_load_training_metrics(self, app_client):
        _, db_file = app_client
        _seed_metrics(db_file)
        conn = sqlite3.connect(str(db_file))
        from src.web.views_training_loaders import load_training_metrics
        m = load_training_metrics(conn)
        conn.close()
        assert m["utrs_val"] == 75.0
        assert m["cirs_val"] == 35.0
        assert m["utrs_json"]["grade"] == "optimal"

    def test_load_training_metrics_empty(self, app_client):
        _, db_file = app_client
        conn = sqlite3.connect(str(db_file))
        from src.web.views_training_loaders import load_training_metrics
        m = load_training_metrics(conn)
        conn.close()
        assert m["utrs_val"] is None
        assert m["cirs_val"] is None

    def test_load_sync_status(self, app_client):
        _, db_file = app_client
        _seed_sync_jobs(db_file)
        conn = sqlite3.connect(str(db_file))
        from src.web.views_training_loaders import load_sync_status
        syncs = load_sync_status(conn)
        conn.close()
        assert len(syncs) == 3
        services = [s["service"] for s in syncs]
        assert "garmin" in services

    def test_load_goal(self, app_client):
        _, db_file = app_client
        _seed_goal(db_file)
        conn = sqlite3.connect(str(db_file))
        from src.web.views_training_loaders import load_goal
        goal = load_goal(conn)
        conn.close()
        assert goal is not None
        assert goal["name"] == "서울마라톤 2026"
