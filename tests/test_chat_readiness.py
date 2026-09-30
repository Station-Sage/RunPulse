"""tests/test_chat_readiness.py — Coach 채팅이 Today·adjuster와 같은 readiness_decision을 쓰는지 검증."""
from __future__ import annotations

import sqlite3
from datetime import date

import pytest

from src.ai.chat_engine_rules import rule_based_response
from src.ai.chat_readiness import attach_readiness, decision_lines, plan_line
from src.ai.ai_context import build_context, format_context_text
from src.db_setup import create_tables, migrate_db
from src.training.adjuster import adjust_todays_plan
from src.training.fatigue import readiness_decision

TODAY = date.today().isoformat()


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    migrate_db(c)
    yield c
    c.close()


def _seed(conn, bb: int, tsb: float, workout: str = "interval", sleep: int = 30):
    conn.execute("INSERT INTO planned_workouts (date, workout_type, distance_km, completed, source)"
                 " VALUES (?, ?, 10.0, 0, 'planner')", (TODAY, workout))
    conn.execute("INSERT OR REPLACE INTO daily_wellness (date, body_battery_high, sleep_score) VALUES (?, ?, ?)",
                 (TODAY, bb, sleep))
    conn.execute("INSERT OR REPLACE INTO metric_store (scope_type, scope_id, metric_name, provider, numeric_value, is_primary)"
                 " VALUES ('daily', ?, 'tsb', 'runpulse', ?, 1)", (TODAY, tsb))
    conn.commit()


def test_adjuster_fatigue_matches_readiness_decision(conn):
    _seed(conn, bb=20, tsb=-30)
    adj = adjust_todays_plan(conn, date=TODAY)
    dec = readiness_decision(conn, date=TODAY)
    assert adj["fatigue_level"] == dec["fatigue_level"] == "high"
    assert adj["tsb"] == dec["tsb"] and adj["wellness"] == dec["wellness"]
    assert adj["adjusted"] and adj["adjusted_type"] == "rest"


def test_build_context_has_decision_and_adjustment(conn):
    _seed(conn, bb=20, tsb=-30)
    ctx = build_context(conn, TODAY)
    assert ctx["readiness_decision"]["fatigue_level"] == "high"
    assert ctx["plan_adjustment"]["adjusted_type"] == "rest"


def test_plan_line_shows_original_and_adjusted(conn):
    _seed(conn, bb=20, tsb=-30)
    ctx = build_context(conn, TODAY)
    line = plan_line(ctx)
    assert "인터벌" in line and "휴식" in line and "조정" in line


def test_chat_verdict_equals_today_headline(conn):
    _seed(conn, bb=20, tsb=-30)
    headline = readiness_decision(conn, date=TODAY)["headline"]
    for msg in ("오늘 훈련 뭐 해?", "회복 상태 어때?"):
        assert headline in rule_based_response(conn, msg)
    assert headline in rule_based_response(conn, "x", chip_id="recovery_advice")
    assert headline in format_context_text(build_context(conn, TODAY))


def test_rested_runner_keeps_planned_session(conn):
    _seed(conn, bb=85, tsb=8, workout="tempo", sleep=80)
    text = rule_based_response(conn, "오늘 훈련 뭐 해?")
    assert "→ 조정" not in text and "템포" in text


def test_no_data_graceful(conn):
    ctx: dict = {}
    attach_readiness(conn, ctx, TODAY)
    assert decision_lines({"readiness_decision": None}) == []
    assert plan_line({}) is None
    assert isinstance(rule_based_response(conn, "오늘 훈련 뭐 해?"), str)
