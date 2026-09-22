"""chat_engine._load_recent_chat()의 thread_id 필터링 — Phase 7 Coach 다중 스레드(D3).

전체 chat() 흐름(외부 provider 호출)은 여기서 다루지 않는다 — thread_id 인자가
기존 v1 /ai-coach 동작(thread_id=None)을 깨지 않는지만 확인.
"""
from __future__ import annotations

from src.ai.chat_engine import _load_recent_chat


def _seed(conn, role, content, thread_id=None):
    conn.execute(
        "INSERT INTO chat_messages (role, content, thread_id) VALUES (?, ?, ?)",
        (role, content, thread_id),
    )


class TestLoadRecentChat:
    def test_default_thread_id_none_ignores_thread(self, db_conn):
        """thread_id=None(기본값) — v1 기존 동작: 전체 최근 메시지, 스레드 무관."""
        _seed(db_conn, "user", "레거시 질문 1", thread_id=None)
        _seed(db_conn, "assistant", "레거시 응답 1", thread_id=None)
        _seed(db_conn, "user", "스레드 질문", thread_id=5)
        db_conn.commit()

        history = _load_recent_chat(db_conn, limit=10)
        contents = [h["content"] for h in history]
        assert "레거시 질문 1" in contents
        assert "스레드 질문" in contents  # thread_id 구분 없이 전부 포함

    def test_thread_id_filters_to_that_thread_only(self, db_conn):
        _seed(db_conn, "user", "스레드1 질문", thread_id=1)
        _seed(db_conn, "assistant", "스레드1 응답", thread_id=1)
        _seed(db_conn, "user", "스레드2 질문", thread_id=2)
        db_conn.commit()

        history = _load_recent_chat(db_conn, limit=10, thread_id=1)
        contents = [h["content"] for h in history]
        assert contents == ["스레드1 질문", "스레드1 응답"]

    def test_empty_thread_returns_empty(self, db_conn):
        assert _load_recent_chat(db_conn, limit=10, thread_id=999) == []
