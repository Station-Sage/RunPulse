"""replanner.py 테스트 — 재조정 규칙 (고강도 이동, 볼륨 축소, 테이퍼 보호)."""

from datetime import date, timedelta
from unittest.mock import patch

import pytest

from src.training.replanner import replan_remaining_week
from src.training.goals import add_goal
from src.utils.db_helpers import upsert_metric


# ── 헬퍼 ────────────────────────────────────────────────────────────────────

def _insert_plan(conn, plan_date: str, wtype: str = "easy",
                 dist: float = 10.0, completed: int = 0) -> int:
    cur = conn.execute(
        "INSERT INTO planned_workouts "
        "(date, workout_type, distance_km, completed, source, goal_id) "
        "VALUES (?,?,?,?,'planner',1)",
        (plan_date, wtype, dist, completed),
    )
    conn.commit()
    return cur.lastrowid


def _skip(conn, plan_id: int) -> None:
    conn.execute(
        "UPDATE planned_workouts SET completed=-1 WHERE id=?", (plan_id,)
    )
    conn.commit()


def _monday_of(d: date) -> date:
    return d - timedelta(days=d.weekday())


# ── Rule 1: 고강도 이동 ───────────────────────────────────────────────────────

def test_rule1_interval_moved_to_easy_day(db_conn):
    """건너뛴 interval → 남은 easy 날로 이동 (Rule 1)."""
    monday = _monday_of(date.today())
    skip_date = monday + timedelta(days=1)   # 화
    target_date = monday + timedelta(days=3)  # 목 (easy)
    future_date = monday + timedelta(days=5)  # 토

    plan_id = _insert_plan(db_conn, skip_date.isoformat(), "interval", 10.0)
    easy_id = _insert_plan(db_conn, target_date.isoformat(), "easy", 10.0)
    _insert_plan(db_conn, future_date.isoformat(), "easy", 8.0)
    _skip(db_conn, plan_id)

    with patch("src.training.replanner.date") as mock_date:
        mock_date.today.return_value = skip_date + timedelta(days=1)
        mock_date.fromisoformat = date.fromisoformat
        result = replan_remaining_week(db_conn, plan_id)

    assert result["moved"] is True
    assert result["target_date"] is not None
    row = db_conn.execute(
        "SELECT workout_type FROM planned_workouts WHERE id=?", (easy_id,)
    ).fetchone()
    assert row[0] == "interval"


def test_rule1_tempo_moved(db_conn):
    """건너뛴 tempo → 남은 rest/easy 날로 이동."""
    monday = _monday_of(date.today())
    skip_date = monday + timedelta(days=1)
    rest_date = monday + timedelta(days=4)

    plan_id = _insert_plan(db_conn, skip_date.isoformat(), "tempo", 12.0)
    rest_id = _insert_plan(db_conn, rest_date.isoformat(), "rest", 0.0)
    _skip(db_conn, plan_id)

    with patch("src.training.replanner.date") as mock_date:
        mock_date.today.return_value = skip_date + timedelta(days=1)
        mock_date.fromisoformat = date.fromisoformat
        result = replan_remaining_week(db_conn, plan_id)

    assert result["moved"] is True


def test_rule1_easy_not_moved(db_conn):
    """건너뛴 easy는 이동 대상 아님 — Rule 1 미적용."""
    monday = _monday_of(date.today())
    skip_date = monday + timedelta(days=1)
    easy_date = monday + timedelta(days=3)

    plan_id = _insert_plan(db_conn, skip_date.isoformat(), "easy", 8.0)
    _insert_plan(db_conn, easy_date.isoformat(), "rest", 0.0)
    _skip(db_conn, plan_id)

    with patch("src.training.replanner.date") as mock_date:
        mock_date.today.return_value = skip_date + timedelta(days=1)
        mock_date.fromisoformat = date.fromisoformat
        result = replan_remaining_week(db_conn, plan_id)

    assert result["moved"] is False


def test_rule1_no_available_slot(db_conn):
    """이동 가능한 날이 없으면 moved=False."""
    monday = _monday_of(date.today())
    skip_date = monday + timedelta(days=1)

    plan_id = _insert_plan(db_conn, skip_date.isoformat(), "interval", 10.0)
    # 남은 날 없음
    _skip(db_conn, plan_id)

    with patch("src.training.replanner.date") as mock_date:
        mock_date.today.return_value = skip_date + timedelta(days=1)
        mock_date.fromisoformat = date.fromisoformat
        result = replan_remaining_week(db_conn, plan_id)

    assert result["moved"] is False


# ── Rule 2: 연속 건너뜀 볼륨 축소 ────────────────────────────────────────────

def test_rule2_consecutive_skips_reduce_volume(db_conn):
    """연속 2회 건너뜀 → 남은 고강도 볼륨 10% 감소 (Gabbett 2016)."""
    monday = _monday_of(date.today())
    skip1 = monday + timedelta(days=1)
    skip2 = monday + timedelta(days=2)
    remaining_date = monday + timedelta(days=4)

    plan1 = _insert_plan(db_conn, skip1.isoformat(), "tempo", 12.0, completed=-1)
    plan2 = _insert_plan(db_conn, skip2.isoformat(), "easy", 8.0)
    remaining_id = _insert_plan(db_conn, remaining_date.isoformat(), "interval", 10.0)
    _skip(db_conn, plan2)

    with patch("src.training.replanner.date") as mock_date:
        mock_date.today.return_value = skip2 + timedelta(days=1)
        mock_date.fromisoformat = date.fromisoformat
        result = replan_remaining_week(db_conn, plan2)

    assert result["volume_reduced"] is True
    row = db_conn.execute(
        "SELECT distance_km FROM planned_workouts WHERE id=?", (remaining_id,)
    ).fetchone()
    assert row[0] == pytest.approx(9.0, rel=0.01)  # 10.0 * 0.90


# ── Rule 3: 피드백 기반 경고 ─────────────────────────────────────────────────

def test_rule3_low_dist_ratio_warning(db_conn):
    """최근 3회 dist_ratio < 0.85 → 볼륨 감소 경고."""
    monday = _monday_of(date.today())
    skip_date = monday + timedelta(days=1)
    plan_id = _insert_plan(db_conn, skip_date.isoformat(), "easy", 8.0)

    # session_outcomes: 최근 3회 dist_ratio 0.70 (< 0.85)
    for i in range(3):
        d = (date.today() - timedelta(days=i + 1)).isoformat()
        db_conn.execute(
            "INSERT INTO session_outcomes "
            "(planned_id, date, dist_ratio, outcome_label) VALUES (?,?,?,'underperformed')",
            (1000 + i, d, 0.70),
        )
    db_conn.commit()
    _skip(db_conn, plan_id)

    with patch("src.training.replanner.date") as mock_date:
        mock_date.today.return_value = skip_date + timedelta(days=1)
        mock_date.fromisoformat = date.fromisoformat
        result = replan_remaining_week(db_conn, plan_id)

    assert len(result["warnings"]) > 0
    assert any("달성률" in w for w in result["warnings"])


# ── Rule 4: 테이퍼 보호 ──────────────────────────────────────────────────────

def test_rule4_taper_no_move(db_conn):
    """레이스 2주 이내: 이동 없이 볼륨 5% 축소 (Mujika & Padilla 2003)."""
    race_date = (date.today() + timedelta(days=10)).isoformat()
    add_goal(db_conn, "테스트레이스", 42.195, race_date=race_date)

    monday = _monday_of(date.today())
    skip_date = monday + timedelta(days=1)
    remaining_date = monday + timedelta(days=3)

    plan_id = _insert_plan(db_conn, skip_date.isoformat(), "interval", 10.0)
    remaining_id = _insert_plan(db_conn, remaining_date.isoformat(), "interval", 10.0)
    _skip(db_conn, plan_id)

    with patch("src.training.replanner.date") as mock_date:
        mock_date.today.return_value = skip_date + timedelta(days=1)
        mock_date.fromisoformat = date.fromisoformat
        result = replan_remaining_week(db_conn, plan_id)

    assert result["moved"] is False
    row = db_conn.execute(
        "SELECT distance_km FROM planned_workouts WHERE id=?", (remaining_id,)
    ).fetchone()
    assert row[0] == pytest.approx(9.5, rel=0.01)  # 10.0 * 0.95


# ── 반환 구조 검증 ────────────────────────────────────────────────────────────

def test_result_has_required_keys(db_conn):
    """반환 dict에 필수 키 존재 확인."""
    monday = _monday_of(date.today())
    skip_date = monday + timedelta(days=1)
    plan_id = _insert_plan(db_conn, skip_date.isoformat(), "easy", 8.0)
    _skip(db_conn, plan_id)

    with patch("src.training.replanner.date") as mock_date:
        mock_date.today.return_value = skip_date + timedelta(days=1)
        mock_date.fromisoformat = date.fromisoformat
        result = replan_remaining_week(db_conn, plan_id)

    required = {"moved", "target_date", "volume_reduced", "message", "changes", "warnings"}
    assert required.issubset(result.keys())


def test_unknown_workout_id_returns_error(db_conn):
    """존재하지 않는 workout_id → moved=False + 메시지."""
    result = replan_remaining_week(db_conn, 99999)
    assert result["moved"] is False
    assert "찾을 수 없습니다" in result["message"]


# ── CRS 기반 Q-day 경고 (crs.evaluate 복원, ADJ-22) ──────────────────────────

_CRS_WARN = "현재 CRS 레벨"


def _replan_with_crs(db_conn, crs_json, *, crs_offset=1, raw=None):
    """today = 건너뜀 다음 날. crs_offset 일 뒤 날짜에 CRS 행을 저장하고 재계획 실행."""
    monday = _monday_of(date.today())
    skip_date = monday + timedelta(days=1)
    today = skip_date + timedelta(days=1)
    plan_id = _insert_plan(db_conn, skip_date.isoformat(), "easy", 8.0)
    _skip(db_conn, plan_id)
    crs_day = (skip_date + timedelta(days=crs_offset)).isoformat()
    if raw is not None:
        db_conn.execute(
            "INSERT INTO metric_store (scope_type, scope_id, metric_name, category, provider, "
            "json_value, is_primary) VALUES ('daily', ?, 'crs', 'readiness', 'p', ?, 1)",
            (crs_day, raw))
        db_conn.commit()
    elif crs_json is not None:
        upsert_metric(db_conn, "daily", crs_day, "crs", "runpulse:formula_v1",
                      numeric_value=50.0, category="readiness", json_value=crs_json)
    with patch("src.training.replanner.date") as mock_date:
        mock_date.today.return_value = today
        mock_date.fromisoformat = date.fromisoformat
        return replan_remaining_week(db_conn, plan_id)


@pytest.mark.parametrize("level,label", [(0, "휴식"), (1, "이지런만")])
def test_crs_low_level_adds_warning(db_conn, level, label):
    result = _replan_with_crs(db_conn, {"level": level, "level_label": label, "crs": 30.0})
    assert any(_CRS_WARN in w and label in w and "이지런으로 전환" in w for w in result["warnings"])


@pytest.mark.parametrize("level", [2, 3, 4])
def test_crs_level_above_z1_no_warning(db_conn, level):
    result = _replan_with_crs(db_conn, {"level": level, "crs": 70.0})
    assert not any(_CRS_WARN in w for w in result["warnings"])


def test_crs_missing_row_no_warning_no_error(db_conn):
    result = _replan_with_crs(db_conn, None)
    assert not any(_CRS_WARN in w for w in result["warnings"])


def test_crs_other_day_row_not_used_as_today(db_conn):
    """오늘이 아닌 날(어제) 저장된 level 0 은 경고로 쓰지 않는다."""
    result = _replan_with_crs(db_conn, {"level": 0, "crs": 10.0}, crs_offset=0)
    assert not any(_CRS_WARN in w for w in result["warnings"])


def test_crs_corrupt_row_no_warning_no_error(db_conn):
    result = _replan_with_crs(db_conn, None, raw="{broken")
    assert not any(_CRS_WARN in w for w in result["warnings"])
