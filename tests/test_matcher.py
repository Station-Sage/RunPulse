"""matcher.py 테스트 — 날짜 기반 매칭 + session_outcomes 저장."""

from datetime import date, timedelta

import pytest

from src.training.matcher import match_week_activities, save_skipped_outcome


# ── 헬퍼 ────────────────────────────────────────────────────────────────────

def _insert_plan(conn, plan_date: str, wtype: str = "easy",
                 dist: float = 10.0, pace_min: int = 300) -> int:
    cur = conn.execute(
        "INSERT INTO planned_workouts (date, workout_type, distance_km, "
        "target_pace_min, source) VALUES (?,?,?,?,'planner')",
        (plan_date, wtype, dist, pace_min),
    )
    conn.commit()
    return cur.lastrowid


_act_counter = 0

def _insert_activity(conn, act_date: str, dist: float = 10.0,
                     pace: int = 305, hr: float = 148.0) -> int:
    """activity_summaries 에 직접 삽입 (v_canonical_activities 뷰 통해 매칭)."""
    global _act_counter
    _act_counter += 1
    cur = conn.execute(
        "INSERT INTO activity_summaries "
        "(source, source_id, start_time, duration_sec, distance_km, "
        " avg_pace_sec_km, avg_hr, activity_type) "
        "VALUES ('garmin', ?, ?, 3600, ?, ?, ?, 'running')",
        (f"ext{_act_counter}", f"{act_date}T08:00:00", dist, pace, hr),
    )
    conn.commit()
    return cur.lastrowid


# ── 단위 테스트: 매칭 ────────────────────────────────────────────────────────

def test_match_week_returns_zero_no_plans(db_conn):
    """계획 없으면 0 반환."""
    monday = date(2026, 4, 6)
    assert match_week_activities(db_conn, monday) == 0


def test_match_week_returns_zero_no_activities(db_conn):
    """계획은 있지만 활동 없으면 0 반환."""
    monday = date(2026, 4, 6)
    _insert_plan(db_conn, "2026-04-07")
    assert match_week_activities(db_conn, monday) == 0


def test_match_week_same_day(db_conn):
    """같은 날 활동이 있으면 1건 매칭."""
    monday = date(2026, 4, 6)
    plan_id = _insert_plan(db_conn, "2026-04-07", dist=10.0)
    _insert_activity(db_conn, "2026-04-07", dist=10.2)

    matched = match_week_activities(db_conn, monday)
    assert matched == 1

    row = db_conn.execute(
        "SELECT completed, matched_activity_id FROM planned_workouts WHERE id=?",
        (plan_id,),
    ).fetchone()
    assert row[0] == 1
    assert row[1] is not None


def test_match_week_updates_completed_flag(db_conn):
    """매칭 후 completed=1 로 업데이트."""
    monday = date(2026, 4, 6)
    plan_id = _insert_plan(db_conn, "2026-04-08", dist=15.0)
    _insert_activity(db_conn, "2026-04-08", dist=14.8)

    match_week_activities(db_conn, monday)

    row = db_conn.execute(
        "SELECT completed FROM planned_workouts WHERE id=?", (plan_id,)
    ).fetchone()
    assert row[0] == 1


def test_match_week_rest_skipped(db_conn):
    """workout_type='rest'는 매칭 대상 제외."""
    monday = date(2026, 4, 6)
    plan_id = _insert_plan(db_conn, "2026-04-09", wtype="rest", dist=0.0)
    _insert_activity(db_conn, "2026-04-09", dist=5.0)

    matched = match_week_activities(db_conn, monday)
    assert matched == 0


def test_match_week_outside_range_ignored(db_conn):
    """주 범위 바깥 활동은 매칭 안 됨."""
    monday = date(2026, 4, 6)
    plan_id = _insert_plan(db_conn, "2026-04-07")
    _insert_activity(db_conn, "2026-04-15", dist=10.0)  # 다음 주

    assert match_week_activities(db_conn, monday) == 0


def test_match_week_idempotent(db_conn):
    """이미 completed=1인 계획은 재매칭 안 됨."""
    monday = date(2026, 4, 6)
    plan_id = _insert_plan(db_conn, "2026-04-07")
    _insert_activity(db_conn, "2026-04-07")

    first = match_week_activities(db_conn, monday)
    second = match_week_activities(db_conn, monday)
    assert first == 1
    assert second == 0


# ── 단위 테스트: session_outcomes ────────────────────────────────────────────

def test_match_saves_session_outcome(db_conn):
    """매칭 성공 시 session_outcomes 레코드 생성."""
    monday = date(2026, 4, 6)
    plan_id = _insert_plan(db_conn, "2026-04-07", dist=10.0, pace_min=300)
    _insert_activity(db_conn, "2026-04-07", dist=10.0, pace=305)

    match_week_activities(db_conn, monday)

    row = db_conn.execute(
        "SELECT planned_id, outcome_label, dist_ratio FROM session_outcomes "
        "WHERE planned_id=?", (plan_id,)
    ).fetchone()
    assert row is not None
    assert row[0] == plan_id
    assert row[1] in ("on_target", "overperformed", "underperformed")
    assert row[2] is not None


def test_match_outcome_on_target(db_conn):
    """dist_ratio ~1.0, pace_delta ~0% → on_target."""
    monday = date(2026, 4, 6)
    plan_id = _insert_plan(db_conn, "2026-04-07", dist=10.0, pace_min=300)
    _insert_activity(db_conn, "2026-04-07", dist=10.0, pace=300)

    match_week_activities(db_conn, monday)

    row = db_conn.execute(
        "SELECT outcome_label FROM session_outcomes WHERE planned_id=?",
        (plan_id,),
    ).fetchone()
    assert row[0] == "on_target"


def test_match_outcome_underperformed(db_conn):
    """실제 거리가 계획의 80% 이하 → underperformed."""
    monday = date(2026, 4, 6)
    plan_id = _insert_plan(db_conn, "2026-04-07", dist=10.0, pace_min=300)
    _insert_activity(db_conn, "2026-04-07", dist=7.5, pace=300)

    match_week_activities(db_conn, monday)

    row = db_conn.execute(
        "SELECT outcome_label FROM session_outcomes WHERE planned_id=?",
        (plan_id,),
    ).fetchone()
    assert row[0] == "underperformed"


# ── 단위 테스트: save_skipped_outcome ────────────────────────────────────────

def test_save_skipped_outcome_inserts(db_conn):
    """건너뜀 처리 시 session_outcomes 에 'skipped' 레코드 삽입."""
    plan_id = _insert_plan(db_conn, "2026-04-07", dist=10.0)

    save_skipped_outcome(db_conn, plan_id, "2026-04-07", 10.0)

    row = db_conn.execute(
        "SELECT outcome_label FROM session_outcomes WHERE planned_id=?",
        (plan_id,),
    ).fetchone()
    assert row is not None
    assert row[0] == "skipped"


def test_save_skipped_outcome_upsert(db_conn):
    """이미 레코드 있으면 outcome_label을 'skipped'으로 업데이트."""
    monday = date(2026, 4, 6)
    plan_id = _insert_plan(db_conn, "2026-04-07", dist=10.0)
    _insert_activity(db_conn, "2026-04-07", dist=10.0)
    match_week_activities(db_conn, monday)

    # 이후 건너뜀으로 변경
    save_skipped_outcome(db_conn, plan_id, "2026-04-07", 10.0)

    row = db_conn.execute(
        "SELECT outcome_label FROM session_outcomes WHERE planned_id=?",
        (plan_id,),
    ).fetchone()
    assert row[0] == "skipped"
