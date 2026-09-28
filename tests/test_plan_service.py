"""tests/test_plan_service.py — plan_service 단위 테스트."""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

import pytest

from src.db_setup import create_tables, migrate_db
from src.services import plan_service
from src.training.goals import add_goal


def _seed_goal(conn) -> int:
    return add_goal(conn, "서울 마라톤", 42.195, race_date="2027-03-15",
                    target_time_sec=14400)


def _seed_workout(conn, goal_date: str, workout_type: str = "easy",
                  completed: int = 0):
    conn.execute(
        "INSERT INTO planned_workouts "
        "(date, workout_type, distance_km, completed, source) "
        "VALUES (?, ?, ?, ?, 'planner')",
        (goal_date, workout_type, 10.0, completed),
    )
    conn.commit()


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.execute("PRAGMA foreign_keys=ON")
    create_tables(c)
    migrate_db(c)
    yield c
    c.close()


# ── get_active_plan ───────────────────────────────────────────────────────────

def test_get_active_plan_no_goal_returns_none(conn):
    assert plan_service.get_active_plan(conn) is None


def test_get_active_plan_returns_structure(conn):
    _seed_goal(conn)
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    _seed_workout(conn, week_start.isoformat(), "easy", completed=0)
    _seed_workout(conn, (week_start + timedelta(days=1)).isoformat(), "long",
                  completed=1)

    result = plan_service.get_active_plan(conn)
    assert result is not None
    assert "goal" in result
    assert result["goal"]["name"] == "서울 마라톤"
    assert result["goal"]["distance_km"] == 42.195
    assert "week_index" in result
    assert result["week_index"] >= 1
    assert "workouts" in result
    assert isinstance(result["workouts"], list)
    assert "ctl_current" in result
    assert "compliance_pct" in result


def test_get_active_plan_by_goal_id(conn):
    goal_id = _seed_goal(conn)
    result = plan_service.get_active_plan(conn, goal_id=goal_id)
    assert result is not None
    assert result["goal"]["id"] == goal_id


def test_get_active_plan_by_invalid_goal_id_returns_none(conn):
    assert plan_service.get_active_plan(conn, goal_id=9999) is None


def test_compliance_pct_with_mixed_workouts(conn):
    """지난 날 수동 완료 2 + 미이행 1 + 휴식 1 → 세션 이행 2/3(휴식 제외). 오늘 요일과 무관하게 과거 날짜로 고정."""
    _seed_goal(conn)
    today = date.today()
    conn.execute("UPDATE goals SET created_at = ?", ((today - timedelta(days=10)).isoformat(),))
    conn.execute("UPDATE goals SET plan_weeks = NULL, race_date = NULL")
    _seed_workout(conn, (today - timedelta(days=5)).isoformat(), "easy", completed=1)
    _seed_workout(conn, (today - timedelta(days=4)).isoformat(), "long", completed=1)
    _seed_workout(conn, (today - timedelta(days=3)).isoformat(), "tempo", completed=0)
    _seed_workout(conn, (today - timedelta(days=2)).isoformat(), "rest", completed=0)

    result = plan_service.get_active_plan(conn)
    assert result["compliance_pct"] == pytest.approx(66.7, abs=0.1)
    assert result["compliance"]["sessions"] == {"done": 2, "total": 3}
    assert result["compliance"]["quality"] == {"done": 0, "total": 1}


def test_compliance_pct_ignores_prior_goal_leftovers(conn):
    """이전(완료/취소된) 목표의 workout이 현재 목표 집계에 섞이지 않아야 한다.

    planned_workouts에는 goal_id 컬럼이 없어 날짜 범위로만 구분한다 — 이전 목표의
    workout이 훨씬 과거 날짜에 있어도 새 목표 생성 이후 범위에는 포함되면 안 된다.
    """
    old_date = (date.today() - timedelta(days=365)).isoformat()
    _seed_workout(conn, old_date, "easy", completed=0)  # 이전 목표의 미완료 워크아웃(오염원)

    _seed_goal(conn)
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    _seed_workout(conn, week_start.isoformat(), "easy", completed=1)
    _seed_workout(conn, (week_start + timedelta(1)).isoformat(), "long", completed=1)

    result = plan_service.get_active_plan(conn)
    # 이전 목표의 미완료 워크아웃이 섞였다면 2/3 = 66.7이 되어야 하지만,
    # 날짜 범위로 걸러지면 2/2 = 100.0
    assert result["compliance_pct"] == pytest.approx(100.0, abs=0.1)


def test_week_index_ignores_prior_goal_leftovers(conn):
    """week_index가 이전 목표의 오래된 workout 날짜가 아닌 현재 목표 생성 시점 기준이어야 한다."""
    old_date = (date.today() - timedelta(days=365)).isoformat()
    _seed_workout(conn, old_date, "easy", completed=0)

    _seed_goal(conn)
    result = plan_service.get_active_plan(conn)
    # created_at이 오늘이므로 1주차여야 한다 (365일 전 기준이면 수십 주차가 됨)
    assert result["week_index"] == 1


# ── get_todays_adjustment ────────────────────────────────────────────────────

def test_get_todays_adjustment_no_plan_returns_none(conn):
    result = plan_service.get_todays_adjustment(conn)
    assert result is None


def test_get_todays_adjustment_with_plan(conn):
    _seed_goal(conn)
    today = date.today().isoformat()
    _seed_workout(conn, today, "easy", completed=0)
    # adjust_todays_plan either returns dict or None depending on data
    result = plan_service.get_todays_adjustment(conn)
    # Result should be dict or None — both acceptable
    assert result is None or isinstance(result, dict)


# ── get_session_detail ────────────────────────────────────────────────────────

def test_get_session_detail_existing_date(conn):
    goal_id = _seed_goal(conn)
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    target = week_start.isoformat()
    _seed_workout(conn, target, "easy")

    result = plan_service.get_session_detail(conn, goal_id, target)
    assert result is not None
    assert result["goal"]["id"] == goal_id
    assert result["workout"]["date"] == target
    assert "week_index" in result
    assert "adjustment" in result
    assert "note" in result


def test_get_session_detail_missing_date_returns_none(conn):
    goal_id = _seed_goal(conn)
    future = (date.today() + timedelta(days=100)).isoformat()
    result = plan_service.get_session_detail(conn, goal_id, future)
    assert result is None


def test_get_session_detail_invalid_goal_id_returns_none(conn):
    today = date.today().isoformat()
    result = plan_service.get_session_detail(conn, 9999, today)
    assert result is None


# ── get_session_note / save_session_note ─────────────────────────────────────

def test_get_session_note_empty(conn):
    assert plan_service.get_session_note(conn, "2026-09-23") is None


def test_save_session_note_and_retrieve(conn):
    plan_service.save_session_note(conn, "2026-09-23", "첫 번째 메모")
    note = plan_service.get_session_note(conn, "2026-09-23")
    assert note == "첫 번째 메모"


def test_save_session_note_upsert(conn):
    """같은 날짜에 두 번 저장하면 마지막 값이 남아야 한다."""
    plan_service.save_session_note(conn, "2026-09-23", "첫 번째")
    plan_service.save_session_note(conn, "2026-09-23", "두 번째")
    note = plan_service.get_session_note(conn, "2026-09-23")
    assert note == "두 번째"


def test_active_plan_next_session_skips_done_and_superseded(tmp_path):
    from datetime import date, timedelta
    import sqlite3
    from src.db_setup import create_tables
    from src.services import plan_service
    c = sqlite3.connect(str(tmp_path / "r.db"))
    create_tables(c)
    today = date.today()
    nxt = today + timedelta(days=1)
    c.execute("INSERT INTO goals (name, distance_km, status) VALUES ('g', 10, 'active')")
    for d, t, done in ((today, "long", 0), (nxt, "easy", 0)):
        c.execute("INSERT INTO planned_workouts (date, workout_type, distance_km, source, completed) VALUES (?,?,?,?,?)",
                  (d.isoformat(), t, 10.0, "planner", done))
    c.execute("INSERT INTO planned_workouts (date, workout_type, source, source_system, completed, matched_activity_id) "
              "VALUES (?, 'easy', 'garmin', 'garmin', 1, 99)", (today.isoformat(),))
    plan = plan_service.get_active_plan(c)
    assert plan["next_session"]["date"] == nxt.isoformat()      # 오늘 추천안은 대체됨 → 내일
