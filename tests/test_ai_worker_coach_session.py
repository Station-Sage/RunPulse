"""ai_worker 코치 스레드 — 상주 세션 풀 연동, ai_sessions 갱신, 퇴역·복구 (가짜 CLI)."""
import json
import sqlite3
import sys
from pathlib import Path

import pytest

from src.ai_worker import main as wm
from src.ai_worker import queue_store as qs
from src.ai_worker import cli_runner as cr
from src.db_schema_v48 import ensure_v48

FAKE = str(Path(__file__).parent / "fixtures" / "fake_claude.py")


@pytest.fixture
def env(tmp_path, monkeypatch):
    db = tmp_path / "running.db"
    c = sqlite3.connect(db)
    ensure_v48(c)
    c.commit()
    c.close()
    real = cr.build_argv

    def fake_argv(**kw):
        sid, resume = kw.get("session_id"), kw.get("resume")
        argv = [sys.executable, FAKE]
        if sid:
            argv += ["--resume" if resume else "--session-id", sid]
        return argv

    monkeypatch.setattr(cr, "build_argv", fake_argv)
    conn = qs.connect(db)
    (tmp_path / "work").mkdir()
    w = wm.Worker("u@x", db, state_dir=tmp_path / "st", work_dir=tmp_path / "work", pythonpath="/p")
    yield w, conn
    w.sessions.close_all()
    conn.close()


def _turn(w, conn, prompt, **extra):
    inp = {"prompt": prompt, **extra}
    jid = qs.enqueue(conn, kind="coach", model="sonnet", input_json=json.dumps(inp), thread_key="coach:1",
                     system_ctx="rules", ctx_hash="h1")
    job = qs.claim(conn, w.worker_id, qs.now_iso())
    w.active.add(jid)
    w.run_job(job)
    r = conn.execute("SELECT * FROM ai_jobs WHERE id=?", (jid,)).fetchone()
    return r


def test_multi_turn_updates_session(env):
    w, conn = env
    r1 = _turn(w, conn, "hello")
    s1 = qs.get_session(conn, "coach:1")
    assert r1["state"] == "done" and s1["turns"] == 1 and s1["state"] == "active"
    r2 = _turn(w, conn, "again")
    s2 = qs.get_session(conn, "coach:1")
    assert r2["result_text"].startswith("turn2") and s2["turns"] == 2 and s2["session_id"] == s1["session_id"]


def test_forced_retire_new_session(env):
    w, conn = env
    _turn(w, conn, "hello")
    sid = qs.get_session(conn, "coach:1")["session_id"]
    r = _turn(w, conn, "redo", retire="regenerate", history=[{"role": "user", "content": "old"}])
    s = qs.get_session(conn, "coach:1")
    assert s["session_id"] != sid and s["turns"] == 1 and r["result_text"].startswith("turn1")
    assert "old" in r["result_text"] or r["state"] == "done"


def test_restart_resumes_active_session(env):
    w, conn = env
    _turn(w, conn, "hello")
    sid = qs.get_session(conn, "coach:1")["session_id"]
    w.sessions.close_all()
    _turn(w, conn, "after restart")
    assert qs.get_session(conn, "coach:1")["session_id"] == sid
