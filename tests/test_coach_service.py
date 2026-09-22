"""coach_service 테스트 — Phase 7a D5.

chat_engine.chat()은 monkeypatch로 결정적 응답으로 대체한다 — coach_service 자체의
스레드/메시지 저장 로직만 검증하는 게 목적이고, 실제 AI provider 체인/rule 기반
fallback(BUG-CHAT-RULE-FALLBACK, 수정 완료 — tests/test_ai_context.py 참조)은
별도로 검증한다.
"""
from __future__ import annotations

import pytest

from src.services import coach_service


@pytest.fixture(autouse=True)
def _fake_ai_chat(monkeypatch):
    """chat_engine.chat()을 결정적 응답으로 대체 — coach_service 로직만 검증."""
    def _fake(conn, user_message, config=None, chip_id=None, thread_id=None):
        return f"[fake] {user_message}에 대한 응답", "fake"

    monkeypatch.setattr("src.ai.chat_engine.chat", _fake)


class TestListThreads:
    def test_empty(self, db_conn):
        assert coach_service.list_threads(db_conn) == []

    def test_lists_with_last_message_preview(self, db_conn):
        result = coach_service.create_thread(db_conn, "오늘 컨디션이 안 좋은데 뭘 해야 할까?")
        threads = coach_service.list_threads(db_conn)
        assert len(threads) == 1
        assert threads[0]["id"] == result["thread"]["id"]
        assert threads[0]["last_message"] == result["message"]["content"]


class TestGetThread:
    def test_not_found(self, db_conn):
        assert coach_service.get_thread(db_conn, 9999) is None

    def test_returns_thread_and_messages(self, db_conn):
        created = coach_service.create_thread(db_conn, "오늘 컨디션이 안 좋은데 뭘 해야 할까?")
        thread_id = created["thread"]["id"]

        detail = coach_service.get_thread(db_conn, thread_id)
        assert detail["thread"]["id"] == thread_id
        assert len(detail["messages"]) == 2
        assert detail["messages"][0]["role"] == "user"
        assert detail["messages"][1]["role"] == "assistant"


class TestCreateThread:
    def test_creates_thread_and_stores_both_messages(self, db_conn):
        result = coach_service.create_thread(db_conn, "레이스 페이스 전략 궁금해")

        thread_id = result["thread"]["id"]
        assert result["thread"]["title"]
        assert result["message"]["role"] == "assistant"
        assert result["message"]["ai_model"] == "fake"

        rows = db_conn.execute(
            "SELECT role, thread_id FROM chat_messages WHERE thread_id = ? ORDER BY id",
            (thread_id,),
        ).fetchall()
        assert [r[0] for r in rows] == ["user", "assistant"]
        assert all(r[1] == thread_id for r in rows)

    def test_title_truncated_for_long_message(self, db_conn):
        long_msg = "가" * 50
        result = coach_service.create_thread(db_conn, long_msg)
        assert len(result["thread"]["title"]) <= 31  # 30자 + '…'
        assert result["thread"]["title"].endswith("…")

    def test_does_not_leak_into_other_threads(self, db_conn):
        """스레드별 대화가 서로 섞이지 않는다 — thread_id 필터링 확인."""
        t1 = coach_service.create_thread(db_conn, "스레드1")
        t2 = coach_service.create_thread(db_conn, "스레드2")
        assert t1["thread"]["id"] != t2["thread"]["id"]

        msgs_1 = db_conn.execute(
            "SELECT content FROM chat_messages WHERE thread_id = ?", (t1["thread"]["id"],)
        ).fetchall()
        assert all("스레드1" in m[0] or m == msgs_1[-1] for m in msgs_1)


class TestAddMessage:
    def test_appends_to_existing_thread(self, db_conn):
        created = coach_service.create_thread(db_conn, "첫 질문")
        thread_id = created["thread"]["id"]

        reply = coach_service.add_message(db_conn, thread_id, "추가 질문")
        assert reply["role"] == "assistant"
        assert reply["thread_id"] == thread_id

        rows = db_conn.execute(
            "SELECT role FROM chat_messages WHERE thread_id = ? ORDER BY id", (thread_id,),
        ).fetchall()
        assert [r[0] for r in rows] == ["user", "assistant", "user", "assistant"]

    def test_updates_thread_timestamp(self, db_conn):
        created = coach_service.create_thread(db_conn, "첫 질문")
        thread_id = created["thread"]["id"]
        before = db_conn.execute(
            "SELECT updated_at FROM chat_threads WHERE id = ?", (thread_id,)
        ).fetchone()[0]

        coach_service.add_message(db_conn, thread_id, "추가 질문")
        after = db_conn.execute(
            "SELECT updated_at FROM chat_threads WHERE id = ?", (thread_id,)
        ).fetchone()[0]
        assert after >= before
