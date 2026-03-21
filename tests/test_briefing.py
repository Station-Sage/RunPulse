"""briefing 모듈 테스트."""
import sqlite3
from datetime import date

import pytest

from src.ai.briefing import build_briefing_prompt, build_chip_prompt, get_clipboard_prompt
from src.db_setup import create_tables


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    yield c
    c.close()


def test_build_briefing_prompt_returns_string(conn):
    result = build_briefing_prompt(conn)
    assert isinstance(result, str)
    assert len(result) > 0


def test_build_briefing_prompt_has_context(conn):
    conn.execute(
        "INSERT INTO activity_summaries"
        " (source, source_id, activity_type, start_time, distance_km,"
        "  duration_sec, avg_pace_sec_km)"
        " VALUES ('garmin', 'g-1', 'running', ?, 10.0, 3000, 300)",
        (date.today().isoformat() + "T06:00:00",),
    )
    conn.commit()
    result = build_briefing_prompt(conn)
    # {{CONTEXT}} 플레이스홀더가 치환됐는지 확인
    assert "{{CONTEXT}}" not in result


def test_build_briefing_prompt_no_placeholder_leak(conn):
    result = build_briefing_prompt(conn)
    assert "{{CONTEXT}}" not in result


def test_build_chip_prompt_today_deep(conn):
    result = build_chip_prompt(conn, "today_deep")
    assert isinstance(result, str)
    assert "{{CONTEXT}}" not in result


def test_build_chip_prompt_weekly_plan(conn):
    result = build_chip_prompt(conn, "weekly_plan")
    assert isinstance(result, str)
    # weekly_plan 템플릿은 JSON 형식 요청을 포함해야 함
    assert "workouts" in result or "json" in result.lower()


def test_build_chip_prompt_unknown_id(conn):
    result = build_chip_prompt(conn, "nonexistent_chip")
    assert "알 수 없는" in result


def test_build_chip_prompt_all_registered_chips(conn):
    """CHIP_REGISTRY의 모든 칩 ID에 대해 오류 없이 프롬프트 생성 확인."""
    from src.ai.suggestions import CHIP_REGISTRY
    for chip_id in CHIP_REGISTRY:
        result = build_chip_prompt(conn, chip_id)
        assert isinstance(result, str), f"{chip_id} 프롬프트 생성 실패"
        assert "{{CONTEXT}}" not in result, f"{chip_id} 플레이스홀더 미치환"


def test_get_clipboard_prompt_briefing_mode(conn):
    result = get_clipboard_prompt(conn, mode="briefing")
    assert isinstance(result, str)
    assert len(result) > 0


def test_get_clipboard_prompt_chip_mode(conn):
    result = get_clipboard_prompt(conn, mode="chip", chip_id="weekly_review")
    assert isinstance(result, str)
    assert len(result) > 0
