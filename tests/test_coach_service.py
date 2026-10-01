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
              require_consent=False, **_hooks):
        return ChatResult(f"[fake] {user_message}에 대한 응답", EngineInfo("ok", "fake", "fake-model"),
                          as_of="2026-09-30")

    monkeypatch.setattr("src.ai.chat_engine.chat_result", _fake)


def _reply(conn, sent):
    """create_thread/add_message 결과의 pending 행을 동기 생성해 완성 답변 뷰를 돌려준다."""
    user, pending = sent["user_message"], sent["assistant_message"]
    return coach_service.generate_reply(conn, pending["thread_id"], pending["id"], user["content"],
                                        chip_id=user.get("chip_id"))


def create_thread(conn, text, chip_id=None, **kw):
    """create_thread + generate_reply — 옛 동기 계약({thread, message})."""
    sent = coach_service.create_thread(conn, text, chip_id=chip_id, **kw)
    return {"thread": sent["thread"], "message": _reply(conn, sent)}


def add_message(conn, thread_id, text, chip_id=None, **kw):
    return _reply(conn, coach_service.add_message(conn, thread_id, text, chip_id=chip_id, **kw))


class TestListThreads:
    def test_empty(self, db_conn):
        assert coach_service.list_threads(db_conn) == []

    def test_lists_with_last_message_preview(self, db_conn):
        result = create_thread(db_conn, "오늘 컨디션이 안 좋은데 뭘 해야 할까?")
        threads = coach_service.list_threads(db_conn)
        assert len(threads) == 1
        assert threads[0]["id"] == result["thread"]["id"]
        assert threads[0]["last_message"] == result["message"]["content"]


class TestGetThread:
    def test_not_found(self, db_conn):
        assert coach_service.get_thread(db_conn, 9999) is None

    def test_returns_thread_and_messages(self, db_conn):
        created = create_thread(db_conn, "오늘 컨디션이 안 좋은데 뭘 해야 할까?")
        thread_id = created["thread"]["id"]

        detail = coach_service.get_thread(db_conn, thread_id)
        assert detail["thread"]["id"] == thread_id
        assert len(detail["messages"]) == 2
        assert detail["messages"][0]["role"] == "user"
        assert detail["messages"][1]["role"] == "assistant"


class TestCreateThread:
    def test_creates_thread_and_stores_both_messages(self, db_conn):
        result = create_thread(db_conn, "레이스 페이스 전략 궁금해")

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
        result = create_thread(db_conn, long_msg)
        assert len(result["thread"]["title"]) <= 31  # 30자 + '…'
        assert result["thread"]["title"].endswith("…")

    def test_does_not_leak_into_other_threads(self, db_conn):
        """스레드별 대화가 서로 섞이지 않는다 — thread_id 필터링 확인."""
        t1 = create_thread(db_conn, "스레드1")
        t2 = create_thread(db_conn, "스레드2")
        assert t1["thread"]["id"] != t2["thread"]["id"]

        msgs_1 = db_conn.execute(
            "SELECT content FROM chat_messages WHERE thread_id = ?", (t1["thread"]["id"],)
        ).fetchall()
        assert all("스레드1" in m[0] or m == msgs_1[-1] for m in msgs_1)


def _seed_tsb(conn):
    conn.execute(
        "INSERT INTO metric_store (scope_type, scope_id, metric_name, provider, numeric_value, is_primary)"
        " VALUES ('daily', '2026-09-30', 'tsb', 'runpulse', -20, 1)")


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
        result = create_thread(db_conn, "레이스 전략 알려줘")
        ev = result["message"]["evidence"]
        assert isinstance(ev, list)

    def test_create_thread_evidence_has_snapshot_and_role(self, db_conn):
        _seed_tsb(db_conn)
        result = create_thread(db_conn, "TSB -20 기준으로 알려줘")
        ev = result["message"]["evidence"]
        assert ev and ev[0]["metric"] == "tsb"
        assert ev[0]["role"] in ("supports", "caveat")
        assert "snapshot" in ev[0] and "drifted" in ev[0]

    def test_create_thread_empty_db_has_no_evidence(self, db_conn):
        result = create_thread(db_conn, "레이스 전략 알려줘")
        assert result["message"]["evidence"] == []

    def test_get_thread_assistant_has_evidence_list(self, db_conn):
        _seed_tsb(db_conn)
        created = create_thread(db_conn, "TSB -20 컨디션")
        thread_id = created["thread"]["id"]
        detail = coach_service.get_thread(db_conn, thread_id)
        assistant_msg = next(m for m in detail["messages"] if m["role"] == "assistant")
        assert "evidence" in assistant_msg
        assert isinstance(assistant_msg["evidence"], list)
        assert len(assistant_msg["evidence"]) > 0

    def test_get_thread_user_message_evidence_empty(self, db_conn):
        created = create_thread(db_conn, "오늘 컨디션")
        thread_id = created["thread"]["id"]
        detail = coach_service.get_thread(db_conn, thread_id)
        user_msg = next(m for m in detail["messages"] if m["role"] == "user")
        assert user_msg.get("evidence") == []
        assert "evidence_json" not in user_msg

    def test_get_thread_no_evidence_json_key(self, db_conn):
        created = create_thread(db_conn, "질문")
        thread_id = created["thread"]["id"]
        detail = coach_service.get_thread(db_conn, thread_id)
        for msg in detail["messages"]:
            assert "evidence_json" not in msg


class TestAddMessage:
    def test_appends_to_existing_thread(self, db_conn):
        created = create_thread(db_conn, "첫 질문")
        thread_id = created["thread"]["id"]

        reply = add_message(db_conn, thread_id, "추가 질문")
        assert reply["role"] == "assistant"
        assert reply["thread_id"] == thread_id

        rows = db_conn.execute(
            "SELECT role FROM chat_messages WHERE thread_id = ? ORDER BY id", (thread_id,),
        ).fetchall()
        assert [r[0] for r in rows] == ["user", "assistant", "user", "assistant"]

    def test_updates_thread_timestamp(self, db_conn):
        created = create_thread(db_conn, "첫 질문")
        thread_id = created["thread"]["id"]
        before = db_conn.execute(
            "SELECT updated_at FROM chat_threads WHERE id = ?", (thread_id,)
        ).fetchone()[0]

        add_message(db_conn, thread_id, "추가 질문")
        after = db_conn.execute(
            "SELECT updated_at FROM chat_threads WHERE id = ?", (thread_id,)
        ).fetchone()[0]
        assert after >= before


class TestEngineState:
    def test_message_carries_engine_view_and_as_of(self, db_conn):
        msg = create_thread(db_conn, "안녕")["message"]
        assert msg["engine"]["status"] == "ok"
        assert msg["engine"]["label"]
        assert msg["as_of"] == "2026-09-30"
        assert msg["status"] == "done"

    def test_get_thread_exposes_engine(self, db_conn):
        tid = create_thread(db_conn, "안녕")["thread"]["id"]
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
        create_thread(db_conn, "안녕")
        assert seen["require_consent"] is True
        assert seen["consent"]["exclude_notes"] is True


class TestRegenerate:
    def test_creates_pending_child_and_hides_parent_after_success(self, db_conn):
        created = create_thread(db_conn, "안녕")
        tid, mid = created["thread"]["id"], created["message"]["id"]
        child = coach_service.regenerate(db_conn, tid, mid)
        assert child["id"] != mid and child["status"] == "pending"
        assert child["parent_message_id"] == mid and child["stream_url"].endswith(f"/{child['id']}/stream")
        # 새 답이 끝나기 전에는 이전 답이 그대로 보인다(자식은 pending 으로 함께 노출)
        done = coach_service.generate_reply(db_conn, tid, child["id"], "안녕")
        assert done["status"] == "done" and done["content"].startswith("[fake] 안녕")
        ids = [m["id"] for m in coach_service.get_thread(db_conn, tid)["messages"]]
        assert mid not in ids and child["id"] in ids and len(ids) == 2

    def test_failed_child_keeps_parent_visible(self, db_conn, monkeypatch):
        created = create_thread(db_conn, "안녕")
        tid, mid = created["thread"]["id"], created["message"]["id"]
        child = coach_service.regenerate(db_conn, tid, mid)

        def _boom(*a, **k):
            raise RuntimeError("boom")

        monkeypatch.setattr("src.ai.chat_engine.chat_result", _boom)
        failed = coach_service.generate_reply(db_conn, tid, child["id"], "안녕")
        assert failed["status"] == "error"
        ids = [m["id"] for m in coach_service.get_thread(db_conn, tid)["messages"]]
        assert mid in ids

    def test_unknown_or_user_message_returns_none(self, db_conn):
        created = create_thread(db_conn, "안녕")
        tid = created["thread"]["id"]
        assert coach_service.regenerate(db_conn, tid, 99999) is None
        user_id = coach_service.get_thread(db_conn, tid)["messages"][0]["id"]
        assert coach_service.regenerate(db_conn, tid, user_id) is None


class TestAsyncContract:
    """3-5: pending 행 선삽입·client_msg_id 멱등·상태 매핑."""

    def test_create_returns_pending_and_user_message_immediately(self, db_conn):
        sent = coach_service.create_thread(db_conn, "안녕", client_msg_id="c1")
        assert sent["created"] is True
        assert sent["user_message"]["content"] == "안녕"
        pending = sent["assistant_message"]
        assert pending["status"] == "pending" and pending["stream_url"]
        msgs = coach_service.get_thread(db_conn, sent["thread"]["id"])["messages"]
        assert [m["role"] for m in msgs] == ["user", "assistant"] and msgs[1]["status"] == "pending"

    def test_create_thread_is_idempotent_by_client_msg_id(self, db_conn):
        first = coach_service.create_thread(db_conn, "안녕", client_msg_id="dup")
        again = coach_service.create_thread(db_conn, "안녕", client_msg_id="dup")
        assert again["created"] is False
        assert again["thread"]["id"] == first["thread"]["id"]
        assert again["user_message"]["id"] == first["user_message"]["id"]
        assert again["assistant_message"]["id"] == first["assistant_message"]["id"]
        assert len(coach_service.list_threads(db_conn)) == 1

    def test_add_message_is_idempotent_by_client_msg_id(self, db_conn):
        tid = create_thread(db_conn, "첫 질문")["thread"]["id"]
        first = coach_service.add_message(db_conn, tid, "둘째", client_msg_id="x1")
        again = coach_service.add_message(db_conn, tid, "둘째", client_msg_id="x1")
        assert first["created"] is True and again["created"] is False
        assert again["user_message"]["id"] == first["user_message"]["id"]
        assert len(coach_service.get_thread(db_conn, tid)["messages"]) == 4

    def test_status_mapping(self, db_conn, monkeypatch):
        from src.ai.chat_engine_result import ChatResult, EngineInfo
        tid = create_thread(db_conn, "시작")["thread"]["id"]

        def _gen(text, engine_status, cancelled=None):
            monkeypatch.setattr("src.ai.chat_engine.chat_result",
                                lambda *a, **k: ChatResult("답", EngineInfo(engine_status, "p", "m")))
            sent = coach_service.add_message(db_conn, tid, text)
            return coach_service.generate_reply(db_conn, tid, sent["assistant_message"]["id"], text,
                                                cancelled=cancelled)

        assert _gen("a", "ok")["status"] == "done"
        assert _gen("b", "fallback")["status"] == "fallback"
        assert _gen("c", "ok", cancelled=lambda: True)["status"] == "cancelled"

    def test_followups_json_preferred_over_engine_json(self, db_conn):
        from src.ai.chat_engine_result import ChatResult, EngineInfo
        tid = create_thread(db_conn, "시작")["thread"]["id"]
        sent = coach_service.add_message(db_conn, tid, "q")
        coach_service.generate_reply(db_conn, tid, sent["assistant_message"]["id"], "q")
        db_conn.execute("UPDATE chat_messages SET followups_json=? WHERE id=?",
                        ('["today_advice"]', sent["assistant_message"]["id"]))
        db_conn.commit()
        last = coach_service.get_thread(db_conn, tid)["messages"][-1]
        assert [f["chip_id"] for f in last["followups"]] == ["today_advice"]


class TestChipAndFollowups:
    """3-4: chip_id 저장·전달, 서버 제공 후속 칩(이미 물은 것 제외)."""

    @pytest.fixture
    def seen(self, monkeypatch):
        from src.ai.chat_engine_result import ChatResult, EngineInfo
        calls = []

        def _fake(conn, user_message, config=None, chip_id=None, thread_id=None, consent=None,
                  require_consent=False, **_hooks):
            calls.append((user_message, chip_id))
            return ChatResult("규칙 답변", EngineInfo("rule", "rule", None), followups=["week_plan", "injury_check"],
                              evidence=[{"kind": "metric", "label": "TSB"}], as_of="2026-09-30")

        monkeypatch.setattr("src.ai.chat_engine.chat_result", _fake)
        return calls

    def test_chip_only_thread_uses_chip_text(self, db_conn, seen):
        result = create_thread(db_conn, None, chip_id="today_advice")
        assert seen == [("오늘 훈련 어떻게 할까요?", "today_advice")]
        assert result["thread"]["title"].startswith("오늘 훈련")
        detail = coach_service.get_thread(db_conn, result["thread"]["id"])
        user, assistant = detail["messages"]
        assert user["chip_id"] == "today_advice" and user["content"] == "오늘 훈련 어떻게 할까요?"
        assert assistant["evidence"] == [{"kind": "metric", "label": "TSB"}] or assistant["evidence"]

    def test_followups_exclude_asked_chips(self, db_conn, seen):
        tid = create_thread(db_conn, None, chip_id="today_advice")["thread"]["id"]
        ids = [f["chip_id"] for f in coach_service.get_thread(db_conn, tid)["messages"][-1]["followups"]]
        assert ids == ["week_plan", "injury_check"]
        add_message(db_conn, tid, None, chip_id="week_plan")
        last = coach_service.get_thread(db_conn, tid)["messages"][-1]
        assert [f["chip_id"] for f in last["followups"]] == ["injury_check"]
        assert last["followups"][0]["text"] == "부상 위험은 없나요?"

    def test_regenerate_keeps_chip_id(self, db_conn, seen):
        created = create_thread(db_conn, None, chip_id="injury_check")
        tid = created["thread"]["id"]
        child = coach_service.regenerate(db_conn, tid, created["message"]["id"])
        coach_service.generate_reply(db_conn, tid, child["id"], "부상 위험은 없나요?", chip_id="injury_check")
        assert seen[-1] == ("부상 위험은 없나요?", "injury_check")

    def test_user_messages_have_no_followups(self, db_conn, seen):
        tid = create_thread(db_conn, "자유 질문")["thread"]["id"]
        assert coach_service.get_thread(db_conn, tid)["messages"][0]["followups"] == []
