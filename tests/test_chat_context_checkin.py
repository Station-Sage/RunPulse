"""tests/test_chat_context_checkin.py — build_checkin_context / format_checkin_line 단위 + 통합."""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from src.ai.chat_context_checkin import build_checkin_context, format_checkin_line
from src.services import today_service


# ─────────────────────────────────────────────────────────────────────────────
# (a) 체크인 없음 → None
# ─────────────────────────────────────────────────────────────────────────────

def test_no_checkin_returns_none(db_conn):
    today = date.today().isoformat()
    assert build_checkin_context(db_conn, today) is None
    assert format_checkin_line(None) is None


# ─────────────────────────────────────────────────────────────────────────────
# (b) 당일 체크인(피로·통증·메모) → dict 일치 + 포맷 문자열 검증
# ─────────────────────────────────────────────────────────────────────────────

def test_today_checkin_fields(db_conn):
    today = date.today().isoformat()
    today_service.save_checkin(db_conn, fatigue=6, pain="mild", note="무릎 뻐근", input_date=today)

    ctx = build_checkin_context(db_conn, today)
    assert ctx is not None
    assert ctx["fatigue"] == 6
    assert ctx["pain"] == "mild"
    assert ctx["note"] == "무릎 뻐근"
    assert ctx["date"] == today

    line = format_checkin_line(ctx)
    assert line is not None
    assert "피로도 6/10" in line
    assert "통증 경미" in line
    assert "무릎 뻐근" in line


# ─────────────────────────────────────────────────────────────────────────────
# (c) 3일 전 체크인 → 무시(None)
# ─────────────────────────────────────────────────────────────────────────────

def test_old_checkin_ignored(db_conn):
    today = date.today().isoformat()
    old_date = (date.today() - timedelta(days=3)).isoformat()
    today_service.save_checkin(db_conn, fatigue=5, input_date=old_date)

    assert build_checkin_context(db_conn, today) is None


# ─────────────────────────────────────────────────────────────────────────────
# (d) 하루 전(UTC 어긋남 대응) 체크인 → 포함
# ─────────────────────────────────────────────────────────────────────────────

def test_yesterday_checkin_included(db_conn):
    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    today_service.save_checkin(db_conn, fatigue=4, input_date=yesterday)

    ctx = build_checkin_context(db_conn, today)
    assert ctx is not None
    assert ctx["fatigue"] == 4


# ─────────────────────────────────────────────────────────────────────────────
# (e) 피로·통증·메모 전부 None/빈 → None
# ─────────────────────────────────────────────────────────────────────────────

def test_empty_checkin_returns_none(db_conn):
    today = date.today().isoformat()
    today_service.save_checkin(db_conn, fatigue=None, pain=None, note=None, input_date=today)

    ctx = build_checkin_context(db_conn, today)
    assert ctx is None


def test_empty_checkin_note_whitespace_returns_none(db_conn):
    today = date.today().isoformat()
    today_service.save_checkin(db_conn, fatigue=None, pain=None, note="   ", input_date=today)

    ctx = build_checkin_context(db_conn, today)
    assert ctx is None


# ─────────────────────────────────────────────────────────────────────────────
# (f) 메모 200자 초과 → 잘림
# ─────────────────────────────────────────────────────────────────────────────

def test_note_truncated_at_200(db_conn):
    today = date.today().isoformat()
    long_note = "a" * 300
    today_service.save_checkin(db_conn, fatigue=5, note=long_note, input_date=today)

    ctx = build_checkin_context(db_conn, today)
    assert ctx is not None
    line = format_checkin_line(ctx)
    assert line is not None
    # 메모 부분만 추출해서 200자 이하인지 확인
    note_start = line.index('메모 "') + len('메모 "')
    note_end = line.rindex('"')
    assert note_end - note_start <= 200


# ─────────────────────────────────────────────────────────────────────────────
# (g) 통합: build_chat_context 결과에 "피로도 7/10" 포함
# ─────────────────────────────────────────────────────────────────────────────

def test_integration_checkin_in_chat_context(db_conn):
    from src.ai.chat_context import build_chat_context

    today = date.today().isoformat()
    today_service.save_checkin(db_conn, fatigue=7, pain="mild", input_date=today)

    result = build_chat_context(db_conn, "오늘 훈련 어때?", provider="rule")
    assert "피로도 7/10" in result


# ─────────────────────────────────────────────────────────────────────────────
# (h) 체크인 없을 때 통합 결과에 "러너 자기 보고" 없음
# ─────────────────────────────────────────────────────────────────────────────

def test_integration_no_checkin_not_in_context(db_conn):
    from src.ai.chat_context import build_chat_context

    result = build_chat_context(db_conn, "오늘 훈련 어때?", provider="rule")
    assert "러너 자기 보고" not in result
