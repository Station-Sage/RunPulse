"""chat_context_scope·exclude_notes — 전송 범위 목록과 메모 제외 (design §4.3)."""
from datetime import date

from src.ai.chat_context import build_chat_context, build_chat_context_scoped
from src.ai.chat_context_scope import describe_scope
from src.services import today_service


def test_describe_scope_marks_note_optional():
    scope = describe_scope({"checkin": {"date": "2026-09-30", "fatigue": 6, "pain": None, "note": "무릎"}})
    items = {s["item"]: s for s in scope}
    assert items["체크인 메모"]["optional"] is True
    assert items["오늘 컨디션 입력(피로·통증)"]["optional"] is False


def test_describe_scope_no_note_when_blank():
    scope = describe_scope({"checkin": {"date": "d", "fatigue": 5, "pain": None, "note": None}})
    assert all(s["item"] != "체크인 메모" for s in scope)


def test_exclude_notes_drops_memo_from_prompt(db_conn):
    today_service.save_checkin(db_conn, fatigue=6, pain="mild", note="비밀메모XYZ", input_date=date.today().isoformat())
    with_note, scope = build_chat_context_scoped(db_conn, "오늘 컨디션 어때?", None, "gemini", False)
    assert "비밀메모XYZ" in with_note
    assert any(s["item"] == "체크인 메모" for s in scope)
    without = build_chat_context(db_conn, "오늘 컨디션 어때?", None, "gemini", exclude_notes=True)
    assert "비밀메모XYZ" not in without
    assert "1 가뿐함 ~ 10 매우 피곤" in without
    _, scope2 = build_chat_context_scoped(db_conn, "오늘 컨디션 어때?", None, "gemini", True)
    assert all(s["item"] != "체크인 메모" for s in scope2)
