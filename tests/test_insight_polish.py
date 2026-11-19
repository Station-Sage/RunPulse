"""능동 인사이트 문장 다듬기·Coach 컨텍스트 블록 (V2-REPAIR D4)."""
import sqlite3

import pytest

from src.ai.chat_context_insight import add_insight_context, format_insight_lines
from src.db_schema_v47 import ensure_v47
from src.services import insight_polish as P
from src.services import insight_service as S

SRC = "최근 훈련 부하가 급격히 늘었어요 (ACWR 1.62). 오늘은 강도를 낮춰 보세요."


def _consent(c, provider="claude_queue"):
    c.execute("CREATE TABLE IF NOT EXISTS coach_consent (id INTEGER PRIMARY KEY, provider TEXT, accepted_at TEXT,"
              " exclude_notes INTEGER, tools_enabled INTEGER, fallback_enabled INTEGER)")
    c.execute("INSERT OR REPLACE INTO coach_consent VALUES (1, ?, 't', 1, 0, 0)", (provider,))


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    ensure_v47(c)
    _consent(c)
    c.execute("INSERT INTO insight_events(kind,severity,as_of,dedupe_key,text) VALUES ('load_spike','watch','2026-11-18','load_spike:global',?)", (SRC,))
    c.commit()
    return c


@pytest.mark.parametrize("out,ok", [
    ("부하가 빠르게 올랐어요(ACWR 1.62). 오늘은 가볍게 가요.", True),
    ("부하가 올랐어요 ACWR 2.5", False),  # 원문에 없는 수치
    ("", False), (None, False), ("x" * 200, False), ("# 제목", False),
])
def test_validate(out, ok):
    assert (P.validate(SRC, out) is not None) is ok


def test_polish_stores_and_exposes(conn):
    assert P.polish_open_events(conn, None, caller=lambda p: "부하가 빠르게 올랐어요(ACWR 1.62).") == 1
    ev = S.list_events(conn)[0]
    assert ev["polished"] and ev["text"].startswith("부하가 빠르게")
    assert P.polish_open_events(conn, None, caller=lambda p: "다시") == 0  # 이미 다듬음


def test_fallback_on_bad_output(conn):
    assert P.polish_open_events(conn, None, caller=lambda p: "ACWR 9.9") == 0
    ev = S.list_events(conn)[0]
    assert not ev["polished"] and ev["text"] == SRC


def test_fallback_on_exception_and_no_provider(conn):
    def boom(p):
        raise RuntimeError("x")
    assert P.polish_open_events(conn, None, caller=boom) == 0
    assert P.polish_open_events(conn, {}) == 0  # provider 없음 → 호출 없이 규칙 문장


def test_stale_polish_invalidated_when_rule_text_changes(conn):
    P.polish_open_events(conn, None, caller=lambda p: "부하가 빠르게 올랐어요(ACWR 1.62).")
    conn.execute("UPDATE insight_events SET text='새 문장 ACWR 1.9'")
    ev = S.list_events(conn)[0]
    assert not ev["polished"] and ev["text"] == "새 문장 ACWR 1.9"


def test_coach_context_block(conn):
    ctx: dict = {}
    add_insight_context(conn, ctx, "2026-11-18")
    assert ctx["insight_events"][0]["severity"] == "watch"
    text = "\n".join(format_insight_lines(ctx))
    assert "열린 알림" in text and "ACWR 1.62" in text


def test_coach_context_empty_has_no_block():
    c = sqlite3.connect(":memory:")
    ensure_v47(c)
    ctx: dict = {}
    add_insight_context(c, ctx, "2026-11-18")
    assert "insight_events" not in ctx


def test_no_consent_no_polish_and_rule_text(conn):
    """동의 없음 → AI 호출 없음, 저장된 다듬은 문장도 숨김(사용자 결정 2026-11-19)."""
    P.polish_open_events(conn, None, caller=lambda p: "부하가 빠르게 올랐어요(ACWR 1.62).")
    conn.execute("DELETE FROM coach_consent")
    assert P.polish_open_events(conn, None, caller=lambda p: pytest.fail("called")) == 0
    ev = S.list_events(conn)[0]
    assert ev["source"] == "rule" and ev["text"] == SRC
