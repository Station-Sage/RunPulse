"""tests/test_fatigue.py — src.training.fatigue.readiness_decision 단위 테스트."""
from __future__ import annotations

import sqlite3
from datetime import date

import pytest

from src.db_setup import create_tables, migrate_db
from src.training.fatigue import readiness_decision


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.execute("PRAGMA foreign_keys=ON")
    create_tables(c)
    migrate_db(c)
    yield c
    c.close()


def _seed_wellness(conn, target_date: str, body_battery: int = 80, sleep_score: int = 75):
    conn.execute(
        "INSERT OR REPLACE INTO daily_wellness (date, body_battery_high, sleep_score)"
        " VALUES (?, ?, ?)",
        (target_date, body_battery, sleep_score),
    )
    conn.commit()


def _seed_tsb(conn, target_date: str, tsb_value: float):
    conn.execute(
        "INSERT OR REPLACE INTO metric_store"
        " (scope_type, scope_id, metric_name, provider, numeric_value, is_primary)"
        " VALUES ('daily', ?, 'tsb', 'runpulse', ?, 1)",
        (target_date, tsb_value),
    )
    conn.commit()


def test_no_data_returns_data_pending_headline(conn):
    decision = readiness_decision(conn)
    assert decision["fatigue_level"] == "low"
    assert decision["tsb"] is None
    assert "수집 중" in decision["headline"]
    assert decision["evidence"] == []


def test_high_fatigue_overrides_good_tsb_headline(conn):
    """웰니스가 나쁘면 TSB가 좋아도(예: 신선) 피로 헤드라인이 우선해야 한다.

    이게 바로 Today(TSB만 봄)와 Coach/plan 조정(wellness+TSB 결합)이 서로 다른
    판정을 내리던 모순 지점이었다 — 통합 후에는 항상 wellness를 함께 본다.
    """
    today = date.today().isoformat()
    _seed_wellness(conn, today, body_battery=20, sleep_score=30)
    _seed_tsb(conn, today, 20.0)  # TSB만 보면 "신선"으로 판정될 값

    decision = readiness_decision(conn)
    assert decision["fatigue_level"] == "high"
    assert "피로가 과도" in decision["headline"]
    metrics = {e["metric"] for e in decision["evidence"]}
    assert {"tsb", "body_battery", "sleep_score"} <= metrics


def test_low_fatigue_falls_back_to_tsb_headline(conn):
    today = date.today().isoformat()
    _seed_wellness(conn, today, body_battery=85, sleep_score=80)
    _seed_tsb(conn, today, -20.0)

    decision = readiness_decision(conn)
    assert decision["fatigue_level"] == "low"
    assert "훈련 부하가 쌓이는 구간" in decision["headline"]


def test_explicit_tsb_overrides_lookup(conn):
    """호출부가 tsb를 직접 넘기면 그 값을 그대로 쓴다(get_latest_tsb 재조회 안 함)."""
    today = date.today().isoformat()
    _seed_tsb(conn, today, -50.0)  # 조회하면 이 값이 나오지만
    decision = readiness_decision(conn, tsb=None)
    assert decision["tsb"] == -50.0

    decision2 = readiness_decision(conn, tsb=3.0)
    assert decision2["tsb"] == 3.0
