"""coach_service 테스트 — Phase 7a D5.

chat_engine.chat_result()는 monkeypatch로 결정적 응답으로 대체한다 — coach_service 자체의
스레드/메시지 저장 로직만 검증하는 게 목적이고, 실제 AI provider 체인/rule 기반
fallback(BUG-CHAT-RULE-FALLBACK, 수정 완료 — tests/test_ai_context.py 참조)은
별도로 검증한다.
"""
from __future__ import annotations

import pytest

from src.services import coach_service


@pytest.fixture(autouse=True)
def _fake_ai_chat(monkeypatch):
    """chat_engine.chat_result()를 결정적 응답으로 대체 — coach_service 로직만 검증."""
    from src.ai.chat_engine_result import ChatResult, EngineInfo

    def _fake(conn, user_message, config=None, chip_id=None, thread_id=None, consent=None,
              require_consent=False):
        return ChatResult(f"[fake] {user_message}에 대한 응답", EngineInfo("ok", "fake", "fake-model"),
                          as_of="2026-09-30")

    monkeypatch.setattr("src.ai.chat_engine.chat_result", _fake)


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


class TestEvidence:
    """Coach 답변 근거(evidence) 저장·반환 테스트."""

    @pytest.fixture(autouse=True)
    def _seed_briefing(self, monkeypatch):
        """get_today_briefing를 결정적 근거로 대체."""
        _ev = [
            {"type": "metric", "metric": "race_days_left", "value": 42, "label": "D-42", "drill": None},
            {"type": "metric", "metric": "tsb", "value": -5.0, "label": "TSB -5.0", "drill": None},
        ]
        monkeypatch.setattr(
            "src.services.today_service.get_today_briefing",
            lambda conn, date=None: {"evidence": _ev},
        )

    def test_create_thread_evidence_is_list(self, db_conn):
        result = coach_service.create_thread(db_conn, "레이스 전략 알려줘")
        ev = result["message"]["evidence"]
        assert isinstance(ev, list)

    def test_create_thread_evidence_first_metric(self, db_conn):
        result = coach_service.create_thread(db_conn, "레이스 전략 알려줘")
        ev = result["message"]["evidence"]
        assert len(ev) > 0
        assert ev[0]["metric"] == "race_days_left"

    def test_get_thread_assistant_has_evidence_list(self, db_conn):
        created = coach_service.create_thread(db_conn, "오늘 컨디션")
        thread_id = created["thread"]["id"]
        detail = coach_service.get_thread(db_conn, thread_id)
        assistant_msg = next(m for m in detail["messages"] if m["role"] == "assistant")
        assert "evidence" in assistant_msg
        assert isinstance(assistant_msg["evidence"], list)
        assert len(assistant_msg["evidence"]) > 0

    def test_get_thread_user_message_evidence_empty(self, db_conn):
        created = coach_service.create_thread(db_conn, "오늘 컨디션")
        thread_id = created["thread"]["id"]
        detail = coach_service.get_thread(db_conn, thread_id)
        user_msg = next(m for m in detail["messages"] if m["role"] == "user")
        assert user_msg.get("evidence") == []
        assert "evidence_json" not in user_msg

    def test_get_thread_no_evidence_json_key(self, db_conn):
        created = coach_service.create_thread(db_conn, "질문")
        thread_id = created["thread"]["id"]
        detail = coach_service.get_thread(db_conn, thread_id)
        for msg in detail["messages"]:
            assert "evidence_json" not in msg

    def test_build_evidence_exception_returns_empty(self, monkeypatch):
        """get_today_briefing가 예외를 발생시키면 build_evidence는 빈 리스트를 반환."""
        monkeypatch.setattr(
            "src.services.today_service.get_today_briefing",
            lambda conn, date=None: (_ for _ in ()).throw(RuntimeError("fail")),
        )
        result = coach_service.build_evidence(None)  # type: ignore[arg-type]
        assert result == []


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


class TestEngineState:
    def test_message_carries_engine_view_and_as_of(self, db_conn):
        msg = coach_service.create_thread(db_conn, "안녕")["message"]
        assert msg["engine"]["status"] == "ok"
        assert msg["engine"]["label"]
        assert msg["as_of"] == "2026-09-30"
        assert msg["status"] == "done"

    def test_get_thread_exposes_engine(self, db_conn):
        tid = coach_service.create_thread(db_conn, "안녕")["thread"]["id"]
        msgs = coach_service.get_thread(db_conn, tid)["messages"]
        assert "engine" not in msgs[0]
        assert msgs[1]["engine"]["provider"] == "fake"

    def test_legacy_message_without_engine_json(self, db_conn):
        tid = db_conn.execute("INSERT INTO chat_threads (title) VALUES ('옛')").lastrowid
        db_conn.execute("INSERT INTO chat_messages (role, content, thread_id) VALUES ('assistant', '옛 답변', ?)", (tid,))
        db_conn.commit()
        msg = coach_service.get_thread(db_conn, tid)["messages"][0]
        assert msg["engine"]["status"] == "legacy_rule"

    def test_engine_called_with_stored_consent_and_require_consent(self, db_conn, monkeypatch):
        from src.services.coach_consent import save_consent
        seen = {}
        orig = __import__("src.ai.chat_engine", fromlist=["x"]).chat_result

        def _spy(conn, msg, **kw):
            seen.update(kw)
            return orig(conn, msg, **kw)

        monkeypatch.setattr("src.ai.chat_engine.chat_result", _spy)
        save_consent(db_conn, "gemini", exclude_notes=True)
        coach_service.create_thread(db_conn, "안녕")
        assert seen["require_consent"] is True
        assert seen["consent"]["exclude_notes"] is True


class TestRegenerate:
    def test_overwrites_assistant_message_in_place(self, db_conn):
        created = coach_service.create_thread(db_conn, "안녕")
        tid, mid = created["thread"]["id"], created["message"]["id"]
        db_conn.execute("UPDATE chat_messages SET content='stale' WHERE id=?", (mid,))
        db_conn.commit()
        msg = coach_service.regenerate(db_conn, tid, mid)
        assert msg["id"] == mid and msg["content"].startswith("[fake] 안녕")
        assert len(coach_service.get_thread(db_conn, tid)["messages"]) == 2

    def test_unknown_or_user_message_returns_none(self, db_conn):
        created = coach_service.create_thread(db_conn, "안녕")
        tid = created["thread"]["id"]
        assert coach_service.regenerate(db_conn, tid, 99999) is None
        user_id = coach_service.get_thread(db_conn, tid)["messages"][0]["id"]
        assert coach_service.regenerate(db_conn, tid, user_id) is None
