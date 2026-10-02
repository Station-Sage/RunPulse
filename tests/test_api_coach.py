"""tests/test_api_coach.py — /api/v1/coach 테스트(스레드·메시지·SSE·취소·재생성·엔진·동의).

chat_engine.chat_result()는 monkeypatch로 결정적 응답 대체 — test_coach_service.py의
_fake_ai_chat 패턴 재사용, AI provider 체인 의존성 제거가 목적.
"""
from __future__ import annotations

import json
import sqlite3

import pytest
from flask import Flask

from src.db_setup import create_tables, migrate_db


@pytest.fixture(autouse=True)
def _fake_ai_chat(monkeypatch):
    from src.ai.chat_engine_result import ChatResult, EngineInfo

    def _fake(conn, user_message, config=None, chip_id=None, thread_id=None, consent=None,
              require_consent=False, on_event=None, cancelled=None):
        if on_event:
            on_event("stage", {"key": "model", "label": "답변 작성 중"})
        return ChatResult(f"[fake] {user_message}에 대한 응답", EngineInfo("ok", "fake", "fake-model"),
                          as_of="2026-09-30")

    monkeypatch.setattr("src.ai.chat_engine.chat_result", _fake)
    from src.services import coach_async
    monkeypatch.setattr(coach_async, "INLINE", True)
    coach_async._RUNS.clear()


@pytest.fixture
def mini_app(tmp_path):
    db_file = tmp_path / "running.db"
    conn = sqlite3.connect(str(db_file))
    create_tables(conn)
    migrate_db(conn)
    conn.close()

    import src.api.routes_coach as routes_coach
    _orig_route = routes_coach.db_path
    routes_coach.db_path = lambda: db_file

    app = Flask(__name__)
    app.config["TESTING"] = True
    from src.api import api_bp
    app.register_blueprint(api_bp)

    with app.test_client() as client:
        yield client

    routes_coach.db_path = _orig_route


def test_list_threads_empty(mini_app):
    res = mini_app.get("/api/v1/coach/threads")
    assert res.status_code == 200
    assert mini_app.get("/api/v1/coach/threads").get_json()["data"]["threads"] == []


def test_create_thread(mini_app):
    res = mini_app.post("/api/v1/coach/threads", json={"initial_message": "오늘 뭐 할까?"})
    assert res.status_code == 201
    body = res.get_json()
    assert body["data"]["thread"]["id"]
    assert body["data"]["user_message"]["content"] == "오늘 뭐 할까?"
    assert body["data"]["assistant_message"]["status"] == "pending"
    assert body["data"]["assistant_message"]["stream_url"].endswith("/stream")


def test_create_thread_missing_message(mini_app):
    res = mini_app.post("/api/v1/coach/threads", json={})
    assert res.status_code == 400
    assert res.get_json()["error"]["code"] == "INVALID_PARAM"


def test_get_thread_detail(mini_app):
    created = mini_app.post("/api/v1/coach/threads", json={"initial_message": "첫 질문"}).get_json()
    thread_id = created["data"]["thread"]["id"]

    res = mini_app.get(f"/api/v1/coach/threads/{thread_id}")
    assert res.status_code == 200
    body = res.get_json()
    assert body["data"]["thread"]["id"] == thread_id
    assert len(body["data"]["messages"]) == 2


def test_get_thread_detail_not_found(mini_app):
    res = mini_app.get("/api/v1/coach/threads/9999")
    assert res.status_code == 404


def test_add_message(mini_app):
    created = mini_app.post("/api/v1/coach/threads", json={"initial_message": "첫 질문"}).get_json()
    thread_id = created["data"]["thread"]["id"]

    res = mini_app.post(f"/api/v1/coach/threads/{thread_id}/messages", json={"content": "추가 질문"})
    assert res.status_code == 201
    body = res.get_json()
    assert body["data"]["user_message"]["content"] == "추가 질문"
    assert body["data"]["assistant_message"]["thread_id"] == thread_id


def test_add_message_thread_not_found(mini_app):
    res = mini_app.post("/api/v1/coach/threads/9999/messages", json={"content": "질문"})
    assert res.status_code == 404


def test_add_message_missing_content(mini_app):
    created = mini_app.post("/api/v1/coach/threads", json={"initial_message": "첫 질문"}).get_json()
    thread_id = created["data"]["thread"]["id"]

    res = mini_app.post(f"/api/v1/coach/threads/{thread_id}/messages", json={})
    assert res.status_code == 400


def test_engine_rule_by_choice_without_consent(mini_app, monkeypatch):
    monkeypatch.setattr("src.api.routes_coach.load_config", lambda user_id=None: {"ai": {"provider": "rule"}})
    data = mini_app.get("/api/v1/coach/engine").get_json()["data"]
    assert data["mode"] == "rule_by_choice"
    assert data["consent"] is None and data["chain"] == []
    assert data["health"]["consecutive_failures"] == 0
    assert any(s["item"] for s in data["scope"])


def test_consent_roundtrip_builds_chain(mini_app, monkeypatch):
    cfg = {"ai": {"provider": "gemini", "gemini_api_key": "k", "groq_api_key": "g"}}
    monkeypatch.setattr("src.api.routes_coach.load_config", lambda user_id=None: cfg)
    assert mini_app.get("/api/v1/coach/engine").get_json()["data"]["chain"] == []
    res = mini_app.put("/api/v1/coach/consent", json={"provider": "gemini", "fallback_enabled": False})
    assert res.status_code == 200
    data = mini_app.get("/api/v1/coach/engine").get_json()["data"]
    assert data["mode"] == "llm"
    assert [c["provider"] for c in data["chain"]] == ["gemini"]
    assert data["consent"]["fallback_enabled"] is False


def test_consent_rejects_bad_provider(mini_app):
    assert mini_app.put("/api/v1/coach/consent", json={"provider": "rule"}).status_code == 400
    assert mini_app.put("/api/v1/coach/consent", json={}).status_code == 400


def test_suggestions_are_handler_backed(mini_app):
    res = mini_app.get("/api/v1/coach/suggestions?at=home")
    assert res.status_code == 200
    sug = res.get_json()["data"]["suggestions"]
    assert sug[0] == {"chip_id": "today_advice", "text": "오늘 훈련 어떻게 할까요?"}
    assert all({"chip_id", "text"} == set(s) for s in sug)


def test_create_thread_by_chip_id(mini_app):
    res = mini_app.post("/api/v1/coach/threads", json={"chip_id": "injury_check"})
    assert res.status_code == 201
    tid = res.get_json()["data"]["thread"]["id"]
    msgs = mini_app.get(f"/api/v1/coach/threads/{tid}").get_json()["data"]["messages"]
    assert msgs[0]["chip_id"] == "injury_check" and msgs[0]["content"] == "부상 위험은 없나요?"
    assert "followups" in msgs[1]


def test_unknown_chip_or_empty_body_rejected(mini_app):
    assert mini_app.post("/api/v1/coach/threads", json={"chip_id": "nope"}).status_code == 400
    assert mini_app.post("/api/v1/coach/threads", json={}).status_code == 400
    tid = mini_app.post("/api/v1/coach/threads", json={"initial_message": "안녕"}).get_json()["data"]["thread"]["id"]
    assert mini_app.post(f"/api/v1/coach/threads/{tid}/messages", json={}).status_code == 400
    assert mini_app.post(f"/api/v1/coach/threads/{tid}/messages", json={"chip_id": "week_plan"}).status_code == 201


def _events(res):
    out = []
    for block in res.get_data(as_text=True).split("\n\n"):
        if not block.strip() or block.startswith(":"):
            continue
        lines = dict(line.split(": ", 1) for line in block.split("\n"))
        out.append((int(lines["id"]), lines["event"], json.loads(lines["data"])))
    return out


def _new(mini_app, text="안녕", **extra):
    return mini_app.post("/api/v1/coach/threads", json={"initial_message": text, **extra})


def test_stream_returns_sse_events_and_headers(mini_app):
    mid = _new(mini_app).get_json()["data"]["assistant_message"]["id"]
    res = mini_app.get(f"/api/v1/coach/messages/{mid}/stream")
    assert res.mimetype == "text/event-stream"
    assert res.headers["Cache-Control"] == "no-cache" and res.headers["X-Accel-Buffering"] == "no"
    events = _events(res)
    assert events[0][1] == "stage" and events[-1][1] == "done"
    assert "[fake]" in "".join(e[2]["text"] for e in events if e[1] == "delta")


def test_stream_resumes_with_last_event_id(mini_app):
    mid = _new(mini_app).get_json()["data"]["assistant_message"]["id"]
    res = mini_app.get(f"/api/v1/coach/messages/{mid}/stream", headers={"Last-Event-ID": "1"})
    assert _events(res)[0][0] == 2
    res = mini_app.get(f"/api/v1/coach/messages/{mid}/stream?last_event_id=2")
    assert _events(res)[0][0] == 3


def test_get_message_poll(mini_app):
    mid = _new(mini_app).get_json()["data"]["assistant_message"]["id"]
    msg = mini_app.get(f"/api/v1/coach/messages/{mid}").get_json()["data"]["message"]
    assert msg["status"] == "done" and "[fake]" in msg["content"]
    assert mini_app.get("/api/v1/coach/messages/9999").status_code == 404


def test_client_msg_id_makes_resend_idempotent(mini_app):
    first = _new(mini_app, client_msg_id="c-1")
    again = _new(mini_app, client_msg_id="c-1")
    assert first.status_code == 201 and again.status_code == 200
    assert first.get_json()["data"]["thread"]["id"] == again.get_json()["data"]["thread"]["id"]
    tid = first.get_json()["data"]["thread"]["id"]
    a = mini_app.post(f"/api/v1/coach/threads/{tid}/messages", json={"content": "또", "client_msg_id": "c-2"})
    b = mini_app.post(f"/api/v1/coach/threads/{tid}/messages", json={"content": "또", "client_msg_id": "c-2"})
    assert (a.status_code, b.status_code) == (201, 200)
    assert a.get_json()["data"]["user_message"]["id"] == b.get_json()["data"]["user_message"]["id"]


def test_cancel_route(mini_app):
    from src.services import coach_async
    mid = _new(mini_app).get_json()["data"]["assistant_message"]["id"]
    run = coach_async._RUNS[mid] = coach_async._Run()
    res = mini_app.post(f"/api/v1/coach/messages/{mid}/cancel")
    assert res.status_code == 200 and res.get_json()["data"]["status"] == "cancelled"
    assert run.cancel.is_set()
    assert mini_app.post("/api/v1/coach/messages/9999/cancel").status_code == 404


def test_regenerate_ai_and_rule_modes(mini_app, monkeypatch):
    seen = []
    from src.ai.chat_engine_result import ChatResult, EngineInfo

    def _spy(conn, user_message, config=None, **kw):
        seen.append((config or {}).get("ai", {}).get("provider"))
        return ChatResult("답", EngineInfo("ok", "fake", "m"))

    monkeypatch.setattr("src.ai.chat_engine.chat_result", _spy)
    mid = _new(mini_app).get_json()["data"]["assistant_message"]["id"]
    res = mini_app.post(f"/api/v1/coach/messages/{mid}/regenerate", json={"mode": "rule"})
    assert res.status_code == 200
    child = res.get_json()["data"]["message"]
    assert child["id"] != mid and seen[-1] == "rule"
    assert mini_app.post(f"/api/v1/coach/messages/{child['id']}/regenerate").status_code == 200
    assert mini_app.post(f"/api/v1/coach/messages/{mid}/regenerate", json={"mode": "x"}).status_code == 400
    assert mini_app.post("/api/v1/coach/messages/9999/regenerate").status_code == 404


def test_activity_context_endpoint(mini_app):
    assert mini_app.get("/api/v1/coach/activity-context").status_code == 400
    assert mini_app.get("/api/v1/coach/activity-context?activity=999").status_code == 404


def test_create_thread_with_activity_context(mini_app):
    res = mini_app.post("/api/v1/coach/threads", json={
        "initial_message": "후반 심박이 걱정돼요", "context": {"kind": "activity", "ref": "7"}})
    assert res.status_code == 201
    assert res.get_json()["data"]["thread"]["context"] == {"kind": "activity", "ref": "7"}


def test_get_thread_returns_context():
    from src.services import coach_service
    import sqlite3
    conn = sqlite3.connect(":memory:")
    from src.db_setup import create_tables
    create_tables(conn)
    tid = conn.execute("INSERT INTO chat_threads (title, context_kind, context_ref) VALUES ('t','activity','7')").lastrowid
    conn.execute("INSERT INTO chat_threads (title) VALUES ('plain')")
    conn.commit()
    assert coach_service.get_thread(conn, tid)["thread"]["context"] == {"kind": "activity", "ref": "7"}
    assert coach_service.get_thread(conn, tid + 1)["thread"]["context"] is None
