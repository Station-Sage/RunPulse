"""suggestions 모듈 테스트."""
import sqlite3
from datetime import date, timedelta

import pytest

from src.ai.suggestions import (
    CHIP_REGISTRY,
    RunnerState,
    get_runner_state,
    rule_based_chips,
)
from src.db_setup import create_tables


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    yield c
    c.close()


def _insert_activity(conn, d=None, distance_km=10.0):
    d = d or date.today().isoformat()
    start = f"{d}T06:00:00"
    conn.execute(
        "INSERT INTO activity_summaries"
        " (source, source_id, activity_type, start_time, distance_km,"
        "  duration_sec, avg_pace_sec_km)"
        " VALUES ('garmin', ?, 'running', ?, ?, 3000, 300)",
        (f"g-{start}", start, distance_km),
    )
    conn.commit()


def _insert_fitness(conn, tsb=5.0, ctl=40.0, atl=42.0):
    conn.execute(
        "INSERT INTO daily_fitness (date, source, ctl, atl, tsb)"
        " VALUES (?, 'intervals', ?, ?, ?)",
        (date.today().isoformat(), ctl, atl, tsb),
    )
    conn.commit()


# ── RunnerState ───────────────────────────────────────────────────────────────

def test_get_runner_state_empty_db(conn):
    state = get_runner_state(conn)
    assert isinstance(state, RunnerState)
    assert state.has_today_run is False
    assert state.acwr is None


def test_get_runner_state_has_activity(conn):
    _insert_activity(conn)
    state = get_runner_state(conn)
    assert state.has_today_run is True
    assert state.weekly_run_count >= 1
    assert state.total_distance_this_week > 0


def test_get_runner_state_tsb(conn):
    _insert_fitness(conn, tsb=-10.0)
    state = get_runner_state(conn)
    assert state.tsb == -10.0


def test_get_runner_state_goal(conn):
    tomorrow = (date.today() + timedelta(days=10)).isoformat()
    conn.execute(
        "INSERT INTO goals (name, distance_km, race_date, status)"
        " VALUES ('테스트 레이스', 10.0, ?, 'active')",
        (tomorrow,),
    )
    conn.commit()
    state = get_runner_state(conn)
    assert state.goal_name == "테스트 레이스"
    assert state.race_days_left == 10


# ── rule_based_chips ──────────────────────────────────────────────────────────

def test_rule_based_chips_returns_list():
    state = RunnerState()
    chips = rule_based_chips(state)
    assert isinstance(chips, list)
    assert 1 <= len(chips) <= 5


def test_rule_based_chips_today_run_first():
    state = RunnerState(has_today_run=True)
    chips = rule_based_chips(state)
    assert chips[0]["id"] == "today_deep"


def test_rule_based_chips_acwr_danger():
    state = RunnerState(acwr=1.6, acwr_status="danger")
    chips = rule_based_chips(state)
    ids = [c["id"] for c in chips]
    assert "injury_risk" in ids


def test_rule_based_chips_poor_recovery():
    state = RunnerState(recovery_grade="poor")
    chips = rule_based_chips(state)
    ids = [c["id"] for c in chips]
    assert "recovery_advice" in ids


def test_rule_based_chips_race_soon():
    state = RunnerState(race_days_left=7, goal_name="시험 레이스")
    chips = rule_based_chips(state)
    ids = [c["id"] for c in chips]
    assert "race_predict" in ids


def test_rule_based_chips_no_duplicates():
    state = RunnerState(
        has_today_run=True,
        acwr_status="caution",
        recovery_grade="poor",
        race_days_left=5,
    )
    chips = rule_based_chips(state)
    labels = [c["label"] for c in chips]
    assert len(labels) == len(set(labels))


def test_rule_based_chips_all_ids_in_registry():
    state = RunnerState()
    chips = rule_based_chips(state)
    for chip in chips:
        assert chip["id"] in CHIP_REGISTRY


# ── CHIP_REGISTRY ─────────────────────────────────────────────────────────────

def test_chip_registry_has_required_keys():
    for cid, info in CHIP_REGISTRY.items():
        assert "label" in info, f"{cid} 에 label 없음"
        assert "template" in info, f"{cid} 에 template 없음"
