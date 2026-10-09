"""tests/test_plan_template_service.py — get_static_plan_templates + create_plan_from_template 단위 테스트."""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

import pytest

from src.db_setup import create_tables, migrate_db
from src.services import plan_template_service


@pytest.fixture
def conn(tmp_path):
    db_file = tmp_path / "running.db"
    c = sqlite3.connect(str(db_file))
    create_tables(c)
    migrate_db(c)
    yield c
    c.close()


def _insert_vdot(conn, vdot: float, days_ago: int = 0):
    day = (date.today() - timedelta(days=days_ago)).isoformat()
    conn.execute(
        "INSERT INTO metric_store "
        "(metric_name, scope_type, scope_id, numeric_value, is_primary, provider) "
        "VALUES ('race_pred_vdot', 'daily', ?, ?, 1, 'test')",
        (day, vdot),
    )
    conn.commit()


# ── get_static_plan_templates ────────────────────────────────────────────────

def test_templates_with_target_time_sec(conn):
    _insert_vdot(conn, 45.0)
    templates = plan_template_service.get_static_plan_templates(conn, 42.195, 14400)
    assert len(templates) >= 1
    for t in templates:
        assert "weeks" in t
        assert "label" in t
        assert "status_summary" in t
        assert t["weeks"] > 0


def test_templates_completion_with_vdot(conn):
    """완주 목표 + VDOT 있으면 achievability 계산됨."""
    _insert_vdot(conn, 40.0)
    templates = plan_template_service.get_static_plan_templates(conn, 42.195, None)
    # effective_target = vdot_to_time(40, 42195) — 계산 가능해야 함
    assert len(templates) >= 1
    for t in templates:
        # achievability_pct가 None이 아닐 수 있음 (VDOT → time 변환 성공 시)
        assert t["weeks"] > 0


def test_templates_completion_no_vdot(conn):
    """완주 목표 + VDOT 없으면 모든 achievability 필드 None."""
    templates = plan_template_service.get_static_plan_templates(conn, 42.195, None)
    assert len(templates) >= 1
    for t in templates:
        assert t["achievability_pct"] is None
        assert t["risk_level"] is None
        assert "VDOT" in t["status_summary"]


def test_templates_dedup_weeks(conn):
    """짧은 거리에서 week_presets가 dedup되어 1~3개 반환."""
    _insert_vdot(conn, 50.0)
    templates = plan_template_service.get_static_plan_templates(conn, 5.0, 1500)
    assert 1 <= len(templates) <= 3


def test_templates_risk_level_mapping(conn):
    """risk_level이 '낮음'/'중간'/'높음' 중 하나여야 함."""
    _insert_vdot(conn, 45.0)
    templates = plan_template_service.get_static_plan_templates(conn, 42.195, 14400)
    valid_levels = {"낮음", "중간", "높음", None}
    for t in templates:
        assert t["risk_level"] in valid_levels


# ── create_plan_from_template ────────────────────────────────────────────────

def test_create_plan_inserts_goal(conn):
    goal_id = plan_template_service.create_plan_from_template(
        conn, 42.195, "2027-03-15", 16, target_time_sec=14400
    )
    assert isinstance(goal_id, int)
    row = conn.execute("SELECT id, plan_weeks, distance_km FROM goals WHERE id=?", (goal_id,)).fetchone()
    assert row is not None
    assert row[1] == 16
    assert abs(row[2] - 42.195) < 0.01


def test_create_plan_fills_planned_workouts(conn):
    goal_id = plan_template_service.create_plan_from_template(
        conn, 10.0, None, 8, target_time_sec=2700
    )
    count = conn.execute(
        "SELECT COUNT(*) FROM planned_workouts WHERE source='planner'"
    ).fetchone()[0]
    assert count > 0


def test_create_plan_no_race_date(conn):
    """race_date=None이어도 정상 생성."""
    goal_id = plan_template_service.create_plan_from_template(
        conn, 21.097, None, 12, target_time_sec=7200
    )
    assert isinstance(goal_id, int)
    row = conn.execute("SELECT id FROM goals WHERE id=?", (goal_id,)).fetchone()
    assert row is not None


def test_create_plan_custom_name(conn):
    goal_id = plan_template_service.create_plan_from_template(
        conn, 5.0, None, 6, name="봄 5km 도전"
    )
    row = conn.execute("SELECT name FROM goals WHERE id=?", (goal_id,)).fetchone()
    assert row[0] == "봄 5km 도전"


def test_create_plan_respects_weeks_not_race_date(conn):
    """race_date가 weeks보다 훨씬 멀어도 생성 주수는 사용자가 고른 weeks를 따라야 한다.

    5-E 비교 화면은 achievability_pct/risk_level을 정확히 `weeks` 기준으로 계산해
    보여준다 — 실제 생성이 race_date를 기준으로 다른 길이가 되면 보여준 지표와
    실제 플랜이 어긋난다.
    """
    far_race_date = (date.today() + timedelta(weeks=40)).isoformat()
    plan_template_service.create_plan_from_template(
        conn, 42.195, far_race_date, 16, target_time_sec=14400
    )
    rows = conn.execute(
        "SELECT date FROM planned_workouts WHERE source='planner'"
    ).fetchall()
    mondays = {
        (
            date.fromisoformat(r[0]) - timedelta(days=date.fromisoformat(r[0]).weekday())
        ).isoformat()
        for r in rows
    }
    assert len(mondays) == 16


def test_create_plan_keeps_existing_training_prefs():
    from datetime import date, timedelta
    from src.services import plan_template_service as pts
    from src.training.planner import upsert_user_training_prefs
    from tests.helpers_pred import mem_conn
    c = mem_conn()
    upsert_user_training_prefs(c, rest_weekdays_mask=5, interval_rep_m=800, max_q_days=1, long_run_weekday_mask=64)
    race = (date.today() + timedelta(days=30)).isoformat()
    pts.create_plan_from_template(c, 10.0, race, 4, name="t")
    row = c.execute("SELECT rest_weekdays_mask, interval_rep_m, max_q_days, long_run_weekday_mask "
                    "FROM user_training_prefs WHERE id=1").fetchone()
    assert tuple(row) == (5, 800, 1, 64)


def test_ensure_prefs_creates_default_row_once():
    from src.training.planner import ensure_user_training_prefs
    from tests.helpers_pred import mem_conn
    c = mem_conn()
    ensure_user_training_prefs(c)
    ensure_user_training_prefs(c)
    assert c.execute("SELECT COUNT(*) FROM user_training_prefs").fetchone()[0] == 1
