"""Coach 규칙 핸들러 레지스트리 (design 30-coach-chat §7.3, §8)."""
from __future__ import annotations

import re
import sqlite3
from datetime import date, timedelta

import pytest

from src.ai.chat_engine_rules import rule_based_response
from src.ai.coach_rule_handlers import (
    FREE_TEXT_HEAD, HANDLERS, answer_chip, answerable_chips, free_text_answer, suggestion_chips,
)
from src.ai.coach_rule_types import CHIP_TEXT
from src.db_setup import create_tables, migrate_db
from src.training.fatigue import readiness_decision

TODAY = date.today()
T = TODAY.isoformat()
RAW_FLOAT = re.compile(r"\d+\.\d{3,}")


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    migrate_db(c)
    yield c
    c.close()


def _wellness(conn, bb=100, sleep=91, tsb=2.6, hrv=None):
    conn.execute("INSERT OR REPLACE INTO daily_wellness (date, body_battery_high, sleep_score) VALUES (?,?,?)",
                 (T, bb, sleep))
    conn.execute("INSERT OR REPLACE INTO metric_store (scope_type, scope_id, metric_name, provider, numeric_value,"
                 " is_primary) VALUES ('daily', ?, 'tsb', 'runpulse', ?, 1)", (T, tsb))
    conn.commit()


def _goal(conn, weeks=12, target=12000, dist=21.0975):
    race = (TODAY + timedelta(weeks=weeks)).isoformat()
    conn.execute("INSERT INTO goals (name, race_date, distance_km, target_time_sec, status)"
                 " VALUES ('가을 하프', ?, ?, ?, 'active')", (race, dist, target))
    conn.commit()
    return race


def test_registry_and_chip_text_match():
    assert set(HANDLERS) == set(CHIP_TEXT)


def test_today_advice_first_sentence_is_today_headline(conn):
    _wellness(conn)
    headline = readiness_decision(conn, date=T)["headline"]
    text = answer_chip(conn, "today_advice").text
    assert text.startswith(headline)
    assert "휴식 권장" not in text


def test_today_advice_no_recovery_row(conn):
    text = answer_chip(conn, "today_advice").text
    assert "회복 데이터 없음" in text


def test_today_advice_checkin_fatigue_steps_down(conn):
    _wellness(conn)
    base = answer_chip(conn, "today_advice").text
    conn.execute("INSERT INTO user_inputs (input_date, input_type, fatigue, pain) VALUES (?, 'checkin', 8, 0)", (T,))
    conn.commit()
    text = answer_chip(conn, "today_advice").text
    assert "피로도 8/10 (1 가뿐함–10 탈진)" in text and "한 단계 낮췄어요" in text
    assert "한 단계 낮췄어요" not in base


def test_unknown_chip_and_free_text_are_honest(conn):
    assert answer_chip(conn, "nope") is None
    ans = rule_based_response(conn, "아무 질문", chip_id="weekly_review")
    assert ans.text.startswith(FREE_TEXT_HEAD)
    assert "AI 코치" not in ans.text
    assert 1 <= len(ans.followups) <= 3 and set(ans.followups) <= set(CHIP_TEXT)


def test_chips_hide_unanswerable(conn):
    chips = answerable_chips(conn)
    assert "goal_feasibility" not in chips and "week_plan" not in chips
    assert "today_advice" in chips and "explain_tsb" in chips
    _goal(conn)
    chips = answerable_chips(conn)
    assert {"goal_feasibility", "race_build", "taper_when"} <= set(chips)
    assert all(c["chip_id"] in HANDLERS for c in suggestion_chips(conn))


def test_every_answerable_chip_answers_without_raw_numbers(conn):
    _wellness(conn)
    _goal(conn)
    for chip in answerable_chips(conn):
        ans = answer_chip(conn, chip)
        assert ans and ans.text, chip
        assert not RAW_FLOAT.search(ans.text), (chip, ans.text)
        assert "초/km" not in ans.text and "AI 코치" not in ans.text, chip
        assert set(ans.followups) <= set(CHIP_TEXT), chip


def test_no_goal_answers_point_to_registering(conn):
    for chip in ("goal_feasibility", "race_build", "taper_when"):
        assert "등록된 목표" in answer_chip(conn, chip).text


def test_goal_without_prediction(conn):
    _goal(conn)
    assert "예측 기록이 아직 없어요" in answer_chip(conn, "goal_feasibility").text


def test_goal_answer_has_goal_prediction_and_gap(conn):
    _goal(conn, target=6600)
    conn.execute("INSERT INTO metric_store (scope_type, scope_id, metric_name, provider, numeric_value, is_primary)"
                 " VALUES ('daily', ?, 'marathon_shape', 'runpulse', 1, 0)", (T,))
    from src.ai import coach_rule_plan_handlers as ph
    hub = {"goal": {"id": 1, "name": "가을 하프", "distance_km": 21.0975, "target_time_sec": 6600,
                    "race_date": T, "days_left": 50, "weeks_left": 7},
           "prediction": {"value_sec": 6900, "history": []}, "projection": {"scenarios": []}}
    orig = ph._hub
    ph._hub = lambda c, t: hub
    try:
        text = ph.goal_feasibility(conn, TODAY).text
    finally:
        ph._hub = orig
    assert "1:50:00" in text and "1:55:00" in text
    assert f"목표보다 5분 느려요" in text and "5:13/km" in text


def test_taper_date(conn):
    race = _goal(conn, weeks=12)
    start = date.fromisoformat(race) - timedelta(days=21)
    text = answer_chip(conn, "taper_when").text
    assert f"{start.month}월 {start.day}일" in text and "25%" in text


def test_week_plan_lists_remaining(conn):
    if TODAY.weekday() == 6:
        pytest.skip("일요일엔 이번 주 남은 훈련이 오늘뿐")
    d = (TODAY + timedelta(days=1)).isoformat()
    conn.execute("INSERT INTO planned_workouts (date, workout_type, distance_km, completed, source)"
                 " VALUES (?, 'easy', 8.0, 0, 'planner')", (d,))
    conn.commit()
    ans = answer_chip(conn, "week_plan")
    assert "이지런 8.00km(저강도)" in ans.text
    assert ans.links and ans.links[0]["href"] == "/v2/coach/plan"


def test_free_text_answer_without_data(conn):
    ans = free_text_answer(conn)
    assert ans.text.startswith(FREE_TEXT_HEAD)
