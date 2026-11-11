"""규칙 답변 자유 입력 키워드 → 칩 순서 (UX C-14). 답을 추측하지 않고 칩 안내만 바꾼다."""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

import pytest

from src.ai.chat_engine_rules import rule_based_response
from src.ai.coach_rule_handlers import FREE_TEXT_HEAD, answerable_chips, free_text_answer
from src.ai.coach_rule_intent import intent_chips, rank_followups
from src.ai.coach_rule_types import CHIP_TEXT
from src.db_setup import create_tables, migrate_db

TODAY = date.today()


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    migrate_db(c)
    yield c
    c.close()


def _goal(conn):
    conn.execute("INSERT INTO goals (name, distance_km, race_date, target_time_sec, status)"
                 " VALUES ('하프', 21.0975, ?, 6300, 'active')", ((TODAY + timedelta(weeks=10)).isoformat(),))
    conn.commit()


def test_intent_chips_keywords_in_priority_order():
    assert intent_chips("무릎이 아파요") == ["injury_check", "explain_cirs"]
    assert intent_chips("요즘 너무 피곤해요")[0] == "today_advice"
    assert intent_chips("테이퍼 언제?")[:2] == ["taper_when", "race_build"]
    assert intent_chips("이번 주 계획 어때?")[0] == "week_plan"
    assert intent_chips("CTL 이 뭐야") == ["explain_ctl"]
    assert intent_chips("동의 테스트") == [] and intent_chips("") == [] and intent_chips(None) == []


def test_rank_followups_falls_back_to_default_order():
    ans = ["today_advice", "injury_check", "explain_tsb", "explain_ctl"]
    assert rank_followups("느린 테스트", ans) == (ans[:3], False)
    # 답할 수 없는 칩(goal_feasibility — 목표 없음)만 가리키면 기존 순서
    assert rank_followups("마라톤 준비", ["today_advice", "injury_check", "explain_tsb"]) == (
        ["today_advice", "injury_check", "explain_tsb"], False)
    assert rank_followups("통증이 있어요", ans) == (["injury_check", "today_advice", "explain_tsb"], True)


def test_free_text_answer_varies_by_question(conn):
    pain = free_text_answer(conn, message="발목 통증이 있어요")
    assert pain.text.startswith(FREE_TEXT_HEAD) and CHIP_TEXT["injury_check"] in pain.text
    assert pain.followups[0] == "injury_check"
    plain = free_text_answer(conn, message="동의 테스트")
    assert plain.followups == answerable_chips(conn)[:3]
    assert "대신" not in plain.text and pain.text != plain.text


def test_rule_based_response_passes_message_and_uses_goal_chips(conn):
    _goal(conn)
    ans = rule_based_response(conn, "마라톤 목표 기록 가능할까?")
    assert ans.followups[:2] == ["goal_feasibility", "race_build"]
    assert ans.text.startswith(FREE_TEXT_HEAD)
