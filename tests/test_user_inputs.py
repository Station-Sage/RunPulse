"""D3 — user_inputs / ai_feedback / chat_threads 테이블 스키마 테스트.

서비스 레이어(today_service.save_checkin, coach_service.*)의 동작 테스트는
tests/test_today_service.py, tests/test_coach_service.py에 있다. 여기는 DDL·제약
조건 자체를 검증한다. wellness_service 연동(test_wellness_merge)은 이번 범위
밖(wellness_service 미변경, plan 참조).
"""
from __future__ import annotations

import sqlite3

import pytest


def _upsert_checkin(conn: sqlite3.Connection, *, input_date: str, fatigue: int,
                     pain: str, note: str | None = None) -> None:
    conn.execute(
        """
        INSERT INTO user_inputs (input_date, input_type, fatigue, pain, note)
        VALUES (?, 'checkin', ?, ?, ?)
        ON CONFLICT(input_date, input_type) DO UPDATE SET
            fatigue = excluded.fatigue,
            pain = excluded.pain,
            note = excluded.note
        """,
        (input_date, fatigue, pain, note),
    )
    conn.commit()


class TestUserInputs:
    def test_save_checkin(self, db_conn):
        _upsert_checkin(db_conn, input_date="2026-09-22", fatigue=6, pain="none")
        row = db_conn.execute(
            "SELECT input_date, input_type, fatigue, pain FROM user_inputs "
            "WHERE input_date = '2026-09-22'"
        ).fetchone()
        assert row == ("2026-09-22", "checkin", 6, "none")

    def test_checkin_unique_per_day(self, db_conn):
        """같은 날짜·타입 재입력 시 UPSERT — 행 추가가 아니라 갱신."""
        _upsert_checkin(db_conn, input_date="2026-09-22", fatigue=6, pain="none")
        _upsert_checkin(db_conn, input_date="2026-09-22", fatigue=8, pain="mild")

        rows = db_conn.execute(
            "SELECT fatigue, pain FROM user_inputs WHERE input_date = '2026-09-22'"
        ).fetchall()
        assert len(rows) == 1
        assert rows[0] == (8, "mild")

    def test_checkin_raw_insert_conflict_without_upsert_raises(self, db_conn):
        """UNIQUE(input_date, input_type) 제약 자체를 직접 확인 (ON CONFLICT 없이 재삽입)."""
        db_conn.execute(
            "INSERT INTO user_inputs (input_date, input_type, fatigue) "
            "VALUES ('2026-09-22', 'checkin', 5)"
        )
        with pytest.raises(sqlite3.IntegrityError):
            db_conn.execute(
                "INSERT INTO user_inputs (input_date, input_type, fatigue) "
                "VALUES ('2026-09-22', 'checkin', 7)"
            )

    def test_activity_id_no_fk_enforcement(self, db_conn):
        """activity_id는 FK 제약이 없다(관례 일치) — 존재하지 않는 활동 id도 저장 가능."""
        db_conn.execute(
            "INSERT INTO user_inputs (input_date, input_type, activity_id) "
            "VALUES ('2026-09-22', 'session_note', 999999)"
        )
        row = db_conn.execute(
            "SELECT activity_id FROM user_inputs WHERE input_date = '2026-09-22'"
        ).fetchone()
        assert row[0] == 999999


class TestAiFeedback:
    def test_insert_feedback(self, db_conn):
        thread_id = db_conn.execute(
            "INSERT INTO chat_threads (title) VALUES ('테스트 스레드')"
        ).lastrowid
        message_id = db_conn.execute(
            "INSERT INTO chat_messages (role, content, thread_id) "
            "VALUES ('assistant', '테스트 응답', ?)", (thread_id,),
        ).lastrowid

        db_conn.execute(
            "INSERT INTO ai_feedback (thread_id, message_id, thumbs) VALUES (?, ?, 'up')",
            (thread_id, message_id),
        )
        row = db_conn.execute(
            "SELECT thumbs FROM ai_feedback WHERE thread_id = ? AND message_id = ?",
            (thread_id, message_id),
        ).fetchone()
        assert row[0] == "up"

    def test_unique_per_thread_message(self, db_conn):
        db_conn.execute(
            "INSERT INTO ai_feedback (thread_id, message_id, thumbs) VALUES (1, 1, 'up')"
        )
        with pytest.raises(sqlite3.IntegrityError):
            db_conn.execute(
                "INSERT INTO ai_feedback (thread_id, message_id, thumbs) VALUES (1, 1, 'down')"
            )


class TestChatThreads:
    def test_chat_messages_thread_id_column_exists(self, db_conn):
        cols = {r[1] for r in db_conn.execute("PRAGMA table_info(chat_messages)").fetchall()}
        assert "thread_id" in cols

    def test_thread_groups_messages(self, db_conn):
        thread_id = db_conn.execute(
            "INSERT INTO chat_threads (title) VALUES ('레이스 페이스 전략')"
        ).lastrowid
        db_conn.execute(
            "INSERT INTO chat_messages (role, content, thread_id) VALUES ('user', '질문', ?)",
            (thread_id,),
        )
        db_conn.execute(
            "INSERT INTO chat_messages (role, content, thread_id) VALUES ('assistant', '응답', ?)",
            (thread_id,),
        )
        # thread_id 없는 레거시 메시지(v1 /ai-coach)는 새 스레드 조회에서 제외되어야 함
        db_conn.execute(
            "INSERT INTO chat_messages (role, content) VALUES ('user', '레거시 대화')"
        )

        rows = db_conn.execute(
            "SELECT content FROM chat_messages WHERE thread_id = ? ORDER BY id", (thread_id,),
        ).fetchall()
        assert [r[0] for r in rows] == ["질문", "응답"]
