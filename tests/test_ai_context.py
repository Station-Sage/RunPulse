"""ai_context 모듈 테스트."""
import sqlite3
from datetime import date

import pytest

from src.ai.ai_context import build_context, format_activity_context, format_context_text
from src.db_setup import create_tables


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    yield c
    c.close()


def _insert_activity(conn, start_time=None, distance_km=10.0, avg_hr=150):
    start_time = start_time or (date.today().isoformat() + "T06:00:00")
    conn.execute(
        "INSERT INTO activity_summaries"
        " (source, source_id, activity_type, start_time, distance_km, duration_sec,"
        "  avg_pace_sec_km, avg_hr)"
        " VALUES ('garmin', ?, 'running', ?, ?, 3000, 300, ?)",
        (f"g-{start_time}", start_time, distance_km, avg_hr),
    )
    conn.commit()


def _insert_wellness(conn, d, body_battery=80, sleep_score=75, hrv_value=55):
    conn.execute(
        "INSERT INTO daily_wellness (date, source, body_battery, sleep_score, hrv_value)"
        " VALUES (?, 'garmin', ?, ?, ?)",
        (d, body_battery, sleep_score, hrv_value),
    )
    conn.commit()


# ── build_context ─────────────────────────────────────────────────────────────

def test_build_context_returns_date(conn):
    ctx = build_context(conn)
    assert ctx["date"] == date.today().isoformat()


def test_build_context_no_activity(conn):
    ctx = build_context(conn)
    assert ctx["today_activity"] is None


def test_build_context_has_activity(conn):
    _insert_activity(conn)
    ctx = build_context(conn)
    assert ctx["today_activity"] is not None
    assert ctx["today_activity"]["distance_km"] == 10.0


def test_build_context_custom_date(conn):
    ctx = build_context(conn, date_str="2026-01-01")
    assert ctx["date"] == "2026-01-01"
    assert ctx["today_activity"] is None


def test_build_context_keys_present(conn):
    ctx = build_context(conn)
    for key in ("date", "today_activity", "recovery", "fitness",
                "weekly", "trends_4w", "acwr", "goal", "plan_today"):
        assert key in ctx


# ── format_context_text ───────────────────────────────────────────────────────

def test_format_context_text_no_activity(conn):
    ctx = build_context(conn)
    text = format_context_text(ctx)
    assert "오늘 활동: 없음" in text


def test_format_context_text_has_activity(conn):
    _insert_activity(conn)
    ctx = build_context(conn)
    text = format_context_text(ctx)
    assert "오늘 활동" in text
    assert "10.0 km" in text or "10" in text


def test_format_context_text_has_sections(conn):
    ctx = build_context(conn)
    text = format_context_text(ctx)
    assert "회복 상태" in text
    assert "분석 기준일" in text


def test_format_context_text_with_wellness(conn):
    today = date.today().isoformat()
    _insert_wellness(conn, today)
    ctx = build_context(conn)
    text = format_context_text(ctx)
    assert "Body Battery" in text


def test_format_context_text_with_goal(conn):
    conn.execute(
        "INSERT INTO goals (name, distance_km, race_date, status)"
        " VALUES ('서울마라톤', 42.195, '2026-11-01', 'active')"
    )
    conn.commit()
    ctx = build_context(conn)
    text = format_context_text(ctx)
    assert "서울마라톤" in text


# ── format_activity_context ───────────────────────────────────────────────────

def test_format_activity_context_no_activity(conn):
    # activity 없으면 빈 활동 상세 반환 (오류 없이)
    text = format_activity_context(conn, activity_id=999)
    assert isinstance(text, str)


def test_format_activity_context_with_activity(conn):
    _insert_activity(conn)
    act_id = conn.execute(
        "SELECT id FROM activity_summaries LIMIT 1"
    ).fetchone()[0]
    text = format_activity_context(conn, activity_id=act_id)
    assert "활동 상세" in text
