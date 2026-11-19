"""deep_thread 테스트 — 'AI 분석'이 코치 스레드의 첫 답변이 된다 (INLINE 모드)."""
import sqlite3

import pytest
from flask import Flask

from src.db_setup import create_tables, migrate_db
from src.services import coach_async, deep_analysis, deep_thread

READY = {"state": "ready", "text": "분석 본문 " * 20, "suggestions": ["왜 그래?", "다음엔?", "c", "d"]}


@pytest.fixture
def db_file(tmp_path, monkeypatch):
    f = tmp_path / "running.db"
    c = sqlite3.connect(str(f))
    create_tables(c)
    migrate_db(c)
    c.close()
    monkeypatch.setattr(coach_async, "INLINE", True)
    coach_async._RUNS.clear()
    return f


def _row(f, mid):
    c = sqlite3.connect(str(f))
    c.row_factory = sqlite3.Row
    try:
        return dict(c.execute("SELECT * FROM chat_messages WHERE id=?", (mid,)).fetchone())
    finally:
        c.close()


def test_start_ready_fills_first_message(db_file, monkeypatch):
    monkeypatch.setattr(deep_analysis, "generate", lambda *a, **k: READY)
    created = deep_thread.start(str(db_file), {}, 7)
    assert created["thread"]["id"]
    row = _row(db_file, created["assistant_message"]["id"])
    assert row["status"] == "done" and row["content"].startswith("분석 본문") and row["ai_model"] == "claude_queue"
    assert row["followups_json"] == '["왜 그래?", "다음엔?", "c"]'
    c = sqlite3.connect(str(db_file))
    assert c.execute("SELECT context_kind, context_ref FROM chat_threads").fetchone() == ("activity", "act:7")


def test_start_failed_and_cancelled(db_file, monkeypatch):
    monkeypatch.setattr(deep_analysis, "generate", lambda *a, **k: {"state": "failed", "reason": "큐 사용 불가"})
    created = deep_thread.start(str(db_file), {}, 1)
    row = _row(db_file, created["assistant_message"]["id"])
    assert row["status"] == "error" and "큐 사용 불가" in row["engine_json"]
    monkeypatch.setattr(deep_analysis, "generate", lambda *a, **k: {"state": "cancelled"})
    created = deep_thread.start(str(db_file), {}, 1)
    assert _row(db_file, created["assistant_message"]["id"])["status"] == "cancelled"


def test_stage_emitter_reports_tools():
    run = coach_async._Run()
    deep_thread._stage_emitter(run)('{"tools": ["get_activity"]}', "")
    deep_thread._stage_emitter(run)(None, "")
    assert [e[2]["key"] for e in run.events if e[1] == "stage"] == ["analyzing", "thinking"]


def test_post_route_returns_thread(db_file, monkeypatch):
    import src.api.routes_deep_analysis as r
    import src.api.routes_plan_replan as rp
    monkeypatch.setattr(r, "db_path", lambda: db_file)
    monkeypatch.setattr(rp, "db_path", lambda: db_file)
    monkeypatch.setattr(r.pcq, "available", lambda conn, cfg: True)
    monkeypatch.setattr(deep_analysis, "generate", lambda *a, **k: READY)
    c = sqlite3.connect(str(db_file))
    c.execute("INSERT INTO activity_summaries(source, source_id, start_time, distance_m) VALUES ('garmin','1','2026-11-18T07:00:00',8000)")
    c.commit()
    c.close()
    app = Flask(__name__)
    from src.api import api_bp
    app.register_blueprint(api_bp)
    res = app.test_client().post("/api/v1/coach/deep", json={}, headers={"Origin": "http://localhost"})
    d = res.get_json()["data"]
    assert res.status_code == 202 and d["thread"]["id"] and d["activity_id"] == 1
