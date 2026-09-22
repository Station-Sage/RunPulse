"""tests/test_briefing.py — briefing.py 클립보드 프롬프트 조립 테스트.

build_briefing_prompt()/build_chip_prompt()는 ai_context.build_context()에 의존한다
(BUG-CHAT-RULE-FALLBACK 수정으로 함께 복구됨 — 이전에는 ImportError로 항상 실패).
"""
from datetime import date

import pytest

from src.ai.briefing import build_briefing_prompt, build_chip_prompt, get_clipboard_prompt

DATE = "2026-04-03"


@pytest.fixture
def conn(db_conn):
    c = db_conn
    c.execute("""
        INSERT INTO activity_summaries
            (source, source_id, name, activity_type, start_time,
             distance_m, duration_sec, avg_pace_sec_km, avg_hr, max_hr, elevation_gain)
        VALUES ('garmin', 'g1', '오후 달리기', 'running', ? || 'T18:00:00Z',
                10020, 3135, 312.8, 155, 178, 120.5)
    """, (DATE,))
    c.commit()
    return c


def test_build_briefing_prompt_contains_context(conn):
    result = build_briefing_prompt(conn)
    assert isinstance(result, str)
    assert "{{CONTEXT}}" not in result  # 치환 완료


def test_build_briefing_prompt_no_data_graceful(db_conn):
    result = build_briefing_prompt(db_conn)
    assert isinstance(result, str)
    assert "{{CONTEXT}}" not in result


def test_build_chip_prompt_weekly_review(conn):
    result = build_chip_prompt(conn, "weekly_review")
    assert isinstance(result, str)
    assert "{{CONTEXT}}" not in result


def test_build_chip_prompt_today_deep_injects_activity_extra(db_conn):
    """today_deep 칩은 오늘 활동 상세(format_activity_context)를 추가로 주입한다.

    build_context()가 항상 실제 오늘 날짜를 기준으로 조회하므로 오늘 날짜로 활동을 심는다.
    """
    today = date.today().isoformat()
    db_conn.execute("""
        INSERT INTO activity_summaries
            (source, source_id, name, activity_type, start_time,
             distance_m, duration_sec, avg_pace_sec_km, avg_hr, max_hr, elevation_gain)
        VALUES ('garmin', 'g1', '오늘 달리기', 'running', ? || 'T18:00:00Z',
                10020, 3135, 312.8, 155, 178, 120.5)
    """, (today,))
    db_conn.commit()

    result = build_chip_prompt(db_conn, "today_deep")
    assert isinstance(result, str)
    assert "활동 상세" in result


def test_build_chip_prompt_unknown_chip(conn):
    result = build_chip_prompt(conn, "no_such_chip")
    assert "알 수 없는 칩" in result


def test_get_clipboard_prompt_briefing_mode(conn):
    result = get_clipboard_prompt(conn, mode="briefing")
    assert isinstance(result, str)


def test_get_clipboard_prompt_chip_mode(conn):
    result = get_clipboard_prompt(conn, mode="chip", chip_id="recovery_advice")
    assert isinstance(result, str)
