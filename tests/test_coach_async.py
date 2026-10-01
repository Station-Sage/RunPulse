"""coach_async 테스트 — 워커 실행·이벤트 로그·SSE 복원·취소 (INLINE 모드로 결정적 실행)."""
from __future__ import annotations

import json
import sqlite3

import pytest

from src.db_setup import create_tables, migrate_db
from src.services import coach_async, coach_service


@pytest.fixture(autouse=True)
def _fake_ai(monkeypatch):
    from src.ai.chat_engine_result import ChatResult, EngineInfo

    def _fake(conn, user_message, config=None, chip_id=None, thread_id=None, consent=None,
              require_consent=False, on_event=None, cancelled=None):
        if on_event:
            on_event("stage", {"key": "model", "label": "답변 작성 중"})
        return ChatResult("가" * 90, EngineInfo("ok", "fake", "fake-model"), as_of="2026-09-30")

    monkeypatch.setattr("src.ai.chat_engine.chat_result", _fake)
    monkeypatch.setattr(coach_async, "INLINE", True)
    coach_async._RUNS.clear()


@pytest.fixture
def db_file(tmp_path):
    f = tmp_path / "running.db"
    conn = sqlite3.connect(str(f))
    create_tables(conn)
    migrate_db(conn)
    conn.close()
    return f


def _sent(db_file, text="질문"):
    conn = sqlite3.connect(str(db_file))
    try:
        return coach_service.create_thread(conn, text)
    finally:
        conn.close()


def _parse(chunks):
    events = []
    for c in chunks:
        if c.startswith(":"):
            continue
        lines = dict(line.split(": ", 1) for line in c.strip().split("\n"))
        events.append((int(lines["id"]), lines["event"], json.loads(lines["data"])))
    return events


def test_start_runs_and_streams_events(db_file):
    mid = _sent(db_file)["assistant_message"]["id"]
    assert coach_async.start(db_file, None, mid) is True
    events = _parse(coach_async.stream(db_file, mid))
    names = [e[1] for e in events]
    assert names[0] == "stage"
    assert names.count("delta") == 3  # 90자 / 40자 청크
    assert names[-1] == "done"
    assert [e[0] for e in events] == list(range(1, len(events) + 1))
    assert "".join(e[2]["text"] for e in events if e[1] == "delta") == "가" * 90
    done = events[-1][2]
    assert done["status"] == "done" and done["as_of"]["basis"] == "generated"


def test_stream_honors_last_event_id(db_file):
    mid = _sent(db_file)["assistant_message"]["id"]
    coach_async.start(db_file, None, mid)
    events = _parse(coach_async.stream(db_file, mid, last_event_id=2))
    assert events[0][0] == 3


def test_stream_restores_from_db_when_log_is_gone(db_file):
    mid = _sent(db_file)["assistant_message"]["id"]
    coach_async.start(db_file, None, mid)
    coach_async._RUNS.clear()
    events = _parse(coach_async.stream(db_file, mid))
    assert [e[1] for e in events][-1] == "done"
    assert "stage" not in [e[1] for e in events]


def test_duplicate_start_while_running_is_rejected(db_file):
    mid = _sent(db_file)["assistant_message"]["id"]
    run = coach_async._RUNS[mid] = coach_async._Run()
    assert coach_async.start(db_file, None, mid) is False
    run.finish()


def test_start_unknown_message_returns_false(db_file):
    assert coach_async.start(db_file, None, 9999) is False


def test_rule_mode_skips_ai(db_file, monkeypatch):
    seen = {}

    def _spy(conn, user_message, config=None, **kw):
        seen["provider"] = (config or {}).get("ai", {}).get("provider")
        from src.ai.chat_engine_result import ChatResult, EngineInfo
        return ChatResult("규칙 답변", EngineInfo("rule_by_choice", "rule", None))

    monkeypatch.setattr("src.ai.chat_engine.chat_result", _spy)
    mid = _sent(db_file)["assistant_message"]["id"]
    coach_async.start(db_file, {"ai": {"provider": "groq"}}, mid, mode="rule")
    assert seen["provider"] == "rule"


def test_worker_exception_emits_error(db_file, monkeypatch):
    def _boom(*a, **k):
        raise RuntimeError("x")

    monkeypatch.setattr("src.ai.chat_engine.chat_result", _boom)
    mid = _sent(db_file)["assistant_message"]["id"]
    coach_async.start(db_file, None, mid)
    events = _parse(coach_async.stream(db_file, mid))
    assert events[-1][1] == "error" and events[-1][2]["status"] == "error"


def test_cancel_running_sets_flag(db_file):
    mid = _sent(db_file)["assistant_message"]["id"]
    run = coach_async._RUNS[mid] = coach_async._Run()
    assert coach_async.cancel(db_file, mid) == "cancelled"
    assert run.cancel.is_set()


def test_cancel_orphan_pending_marks_row(db_file):
    mid = _sent(db_file)["assistant_message"]["id"]
    assert coach_async.cancel(db_file, mid) == "cancelled"
    conn = sqlite3.connect(str(db_file))
    assert conn.execute("SELECT status FROM chat_messages WHERE id=?", (mid,)).fetchone()[0] == "cancelled"
    assert coach_async.cancel(db_file, 9999) is None


def test_orphan_pending_stream_becomes_error(db_file):
    mid = _sent(db_file)["assistant_message"]["id"]
    events = _parse(coach_async.stream(db_file, mid))
    assert events == [(1, "error", {"status": "error", "reason": "interrupted", "attempts": []})]
    conn = sqlite3.connect(str(db_file))
    assert conn.execute("SELECT status FROM chat_messages WHERE id=?", (mid,)).fetchone()[0] == "error"


def test_source_text_follows_regenerate_chain(db_file):
    sent = _sent(db_file, "원래 질문")
    conn = sqlite3.connect(str(db_file))
    mid = sent["assistant_message"]["id"]
    thread_id = sent["thread"]["id"]
    coach_service.generate_reply(conn, thread_id, mid, "원래 질문")
    child = coach_service.regenerate(conn, thread_id, mid)
    tid, text, _ = coach_async.source_text(conn, child["id"])
    assert (tid, text) == (thread_id, "원래 질문")
