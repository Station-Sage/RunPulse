"""Phase G: 목표 관리 개선 테스트 (G-1 ~ G-4)."""
from __future__ import annotations

import json
import sqlite3
from datetime import date, timedelta

import pytest

from src.db_setup import create_tables, migrate_db

def initialize_db(conn):
    create_tables(conn)
    migrate_db(conn)
from src.training.goals import add_goal, list_goals
from src.web.views_training_loaders import (
    _goal_date_range,
    load_goal_weeks,
    load_goals_with_stats,
)
from src.web.views_training_goals import (
    render_goals_panel,
    render_goal_detail_html,
)


# ── fixture ──────────────────────────────────────────────────────────────

@pytest.fixture()
def conn():
    c = sqlite3.connect(":memory:")
    initialize_db(c)
    yield c
    c.close()


def _add_workout(conn, d: str, wtype: str = "easy", km: float = 5.0,
                 completed: int = 0):
    conn.execute(
        """INSERT INTO planned_workouts
           (date, workout_type, distance_km, completed, source)
           VALUES (?, ?, ?, ?, 'test')""",
        (d, wtype, km, completed),
    )
    conn.commit()


# ── G-1: load_goals_with_stats ───────────────────────────────────────────

def test_load_goals_with_stats_empty(conn):
    result = load_goals_with_stats(conn)
    assert result == []


def test_load_goals_with_stats_counts(conn):
    gid = add_goal(conn, "테스트 목표", 10.0,
                   race_date=(date.today() + timedelta(weeks=8)).isoformat())
    today = date.today().isoformat()
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    _add_workout(conn, today, "easy", 5.0, completed=1)
    _add_workout(conn, tomorrow, "tempo", 8.0, completed=0)
    _add_workout(conn, today, "rest", completed=0)  # rest 제외

    goals = load_goals_with_stats(conn)
    assert len(goals) == 1
    g = goals[0]
    assert g["total_count"] == 2      # rest 제외
    assert g["completed_count"] == 1
    assert g["id"] == gid


def test_load_goals_with_stats_status_all(conn):
    add_goal(conn, "활성", 10.0)
    conn.execute("INSERT INTO goals (name, distance_km, status) VALUES (?,?,?)",
                 ("취소됨", 5.0, "cancelled"))
    conn.commit()
    goals = load_goals_with_stats(conn)
    statuses = {g["status"] for g in goals}
    assert "active" in statuses
    assert "cancelled" in statuses


# ── G-1: 렌더링 ─────────────────────────────────────────────────────────

def test_render_goals_panel_empty():
    html = render_goals_panel([])
    assert "설정된 목표가 없습니다" in html
    assert "새 목표 만들기" in html


def test_render_goals_panel_with_goals():
    goals = [
        {"id": 1, "name": "서울마라톤", "distance_km": 42.195,
         "race_date": "2026-11-01", "status": "active",
         "target_time_sec": 10800, "target_pace_sec_km": None,
         "completed_count": 5, "total_count": 20},
    ]
    html = render_goals_panel(goals)
    assert "서울마라톤" in html
    assert "활성" in html
    assert "5/20" in html
    assert "rpGoalToggle(1)" in html


def test_render_goals_panel_d_day():
    future = (date.today() + timedelta(days=30)).isoformat()
    goals = [
        {"id": 2, "name": "테스트", "distance_km": 10.0,
         "race_date": future, "status": "active",
         "completed_count": 0, "total_count": 0},
    ]
    html = render_goals_panel(goals)
    assert "D-30" in html


# ── G-2: 드릴다운 ────────────────────────────────────────────────────────

def test_load_goal_weeks(conn):
    gid = add_goal(conn, "Test", 10.0,
                   race_date=(date.today() + timedelta(weeks=4)).isoformat())
    from src.training.goals import get_goal
    goal = get_goal(conn, gid)
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    _add_workout(conn, week_start.isoformat(), "easy", 5.0, completed=1)
    _add_workout(conn, (week_start + timedelta(days=2)).isoformat(), "tempo", 8.0)

    weeks = load_goal_weeks(conn, goal)
    assert len(weeks) >= 1
    cur = next((w for w in weeks if w["is_current"]), None)
    assert cur is not None
    assert cur["completed_count"] == 1
    assert cur["total_count"] == 2


def test_render_goal_detail_html():
    goal = {"id": 3, "name": "G", "status": "active", "distance_km": 10.0}
    weeks = [
        {"week_start": date.today(), "is_current": True,
         "total_km": 30.0, "total_count": 4, "completed_count": 2},
    ]
    html = render_goal_detail_html(goal, weeks, [])
    assert "W1" in html
    assert "2/4" in html
    assert "목표 취소" in html


def test_render_goal_detail_no_delete_for_cancelled():
    goal = {"id": 4, "name": "G2", "status": "cancelled", "distance_km": 5.0}
    html = render_goal_detail_html(goal, [], [])
    assert "목표 취소" not in html


# ── G-4: 날짜 범위 + 가져오기 ────────────────────────────────────────────

def test_goal_date_range_with_race_date():
    # 2026-01-01(목요일) → 해당 주 월요일 = 2025-12-29
    goal = {
        "created_at": "2026-01-01 00:00:00",
        "race_date": "2026-04-01",
        "plan_weeks": 12,
    }
    start, end = _goal_date_range(goal)
    assert start == "2025-12-29"   # Monday of 2026-01-01's week
    assert end == "2026-04-08"     # race_date + 7days


def test_goal_date_range_with_plan_weeks():
    # 2026-01-01(목요일) → 해당 주 월요일 = 2025-12-29
    goal = {
        "created_at": "2026-01-01 00:00:00",
        "race_date": None,
        "plan_weeks": 8,
    }
    start, end = _goal_date_range(goal)
    assert start == "2025-12-29"   # Monday of 2026-01-01's week
    expected_end = (date(2025, 12, 29) + timedelta(weeks=9)).isoformat()
    assert end == expected_end


def test_import_all(conn):
    """G-4: 전체 가져오기 — 워크아웃 복사 후 개수 검증."""
    src_goal_id = add_goal(conn, "소스", 10.0,
                           race_date=(date.today() + timedelta(weeks=4)).isoformat())
    base = date.today() - timedelta(days=date.today().weekday())
    for i in range(5):
        _add_workout(conn, (base + timedelta(days=i)).isoformat(), "easy")

    from src.training.goals import get_goal
    from src.web.views_training_loaders import _goal_date_range
    src_goal = get_goal(conn, src_goal_id)
    q_start, q_end = _goal_date_range(src_goal)

    rows = conn.execute(
        "SELECT date, workout_type, distance_km FROM planned_workouts "
        "WHERE date >= ? AND date <= ? AND workout_type != 'rest'",
        (q_start, q_end),
    ).fetchall()
    assert len(rows) == 5

    # 오프셋 복사
    from datetime import timedelta as _td
    new_start = base + timedelta(weeks=4)
    offset = (new_start - base).days
    for r in rows:
        new_d = (date.fromisoformat(r[0]) + _td(days=offset)).isoformat()
        conn.execute(
            "INSERT INTO planned_workouts "
            "(date, workout_type, distance_km, completed, source) "
            "VALUES (?, ?, ?, 0, 'imported')",
            (new_d, r[1], r[2]),
        )
    conn.commit()

    imported = conn.execute(
        "SELECT COUNT(*) FROM planned_workouts WHERE source = 'imported'"
    ).fetchone()[0]
    assert imported == 5
