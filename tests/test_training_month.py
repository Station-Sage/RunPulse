"""E-2: 월간 캘린더 뷰 테스트."""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from pathlib import Path

import pytest
from flask import Flask

from src.db_setup import create_tables, migrate_db
from src.web.views_training_month import render_month_calendar, _view_tabs
from src.web.views_training_loaders import load_month_workouts


@pytest.fixture
def db_file(tmp_path) -> Path:
    path = tmp_path / "test_month.db"
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    with sqlite3.connect(str(path)) as conn:
        create_tables(conn)
        migrate_db(conn)
        # 4주치 워크아웃 생성
        for offset in range(28):
            d = week_start + timedelta(days=offset)
            wtype = "rest" if d.weekday() == 6 else "easy"
            conn.execute(
                "INSERT INTO planned_workouts (date, workout_type, distance_km, source)"
                " VALUES (?, ?, ?, 'manual')",
                (d.isoformat(), wtype, 10.0 if wtype != "rest" else None),
            )
        conn.commit()
    return path


class TestLoadMonthWorkouts:
    def test_returns_4_weeks(self, db_file):
        with sqlite3.connect(str(db_file)) as conn:
            weeks = load_month_workouts(conn, week_offset=0)
        assert len(weeks) == 4

    def test_each_tuple_has_workouts_and_date(self, db_file):
        with sqlite3.connect(str(db_file)) as conn:
            weeks = load_month_workouts(conn, week_offset=0)
        for workouts, ws in weeks:
            assert isinstance(workouts, list)
            assert isinstance(ws, date)

    def test_week_offset_shifts_start(self, db_file):
        today = date.today()
        base_week = today - timedelta(days=today.weekday())
        with sqlite3.connect(str(db_file)) as conn:
            weeks0 = load_month_workouts(conn, week_offset=0)
            weeks1 = load_month_workouts(conn, week_offset=1)
        assert weeks0[0][1] == base_week
        assert weeks1[0][1] == base_week + timedelta(weeks=1)


class TestRenderMonthCalendar:
    def test_returns_html_string(self, db_file):
        with sqlite3.connect(str(db_file)) as conn:
            weeks_data = load_month_workouts(conn, week_offset=0)
        html = render_month_calendar(weeks_data)
        assert isinstance(html, str)
        assert len(html) > 100

    def test_has_rp_calendar_id(self, db_file):
        with sqlite3.connect(str(db_file)) as conn:
            weeks_data = load_month_workouts(conn, week_offset=0)
        html = render_month_calendar(weeks_data)
        assert "id='rp-calendar'" in html

    def test_shows_day_names(self, db_file):
        with sqlite3.connect(str(db_file)) as conn:
            weeks_data = load_month_workouts(conn, week_offset=0)
        html = render_month_calendar(weeks_data)
        for day in ["월", "화", "수", "목", "금", "토", "일"]:
            assert day in html

    def test_empty_weeks_graceful(self):
        html = render_month_calendar([])
        assert "없습니다" in html

    def test_actual_activities_shown(self, db_file):
        today = date.today()
        actual = {today.isoformat(): {"km": 9.5, "pace": 300, "hr": 145}}
        with sqlite3.connect(str(db_file)) as conn:
            weeks_data = load_month_workouts(conn, week_offset=0)
        html = render_month_calendar(weeks_data, actual_activities=actual)
        assert "9k" in html or "9.5" in html or "✓" in html


class TestViewTabs:
    def test_contains_all_three_tabs(self):
        html = _view_tabs(0, "month")
        assert "주간" in html
        assert "월간" in html
        assert "전체" in html

    def test_month_active_highlighted(self):
        html = _view_tabs(0, "month")
        # 월간 탭이 활성 색상(cyan)
        assert "#00d4ff" in html

    def test_week_tab_links_correctly(self):
        html = _view_tabs(2, "week")
        assert "week=2" in html
        assert "view=month" in html
