"""ai_worker.main — tick/claim/settle, 쿼터 일시정지, 연속 오류 자가정지, preflight, 취소 (가짜 runner)."""
import json
import sqlite3

import pytest

from src.ai_worker import cli_runner as cr
from src.ai_worker import main as wm
from src.ai_worker import queue_store as qs
from src.db_schema_v48 import ensure_v48


@pytest.fixture
def env(tmp_path):
    db = tmp_path / "running.db"
    c = sqlite3.connect(db)
    ensure_v48(c)
    c.commit()
    c.close()
    conn = qs.connect(db)
    yield db, conn, tmp_path
    conn.close()


def _worker(db, tmp, runner, **kw):
    return wm.Worker("u@x", db, state_dir=tmp / "st", work_dir=tmp / "work", pythonpath="/p",
                     runner=runner, **kw)


def _ok(argv, **k):
    return cr.RunResult(text="안녕", session_id="S", got_result=True, tokens_in=3, tokens_out=2)


def _job(conn, **kw):
    d = dict(kind="ping", model="haiku", input_json=json.dumps({"prompt": "hi"}))
    d.update(kw)
    return qs.enqueue(conn, **d)


def _row(conn, jid):
    return conn.execute("SELECT * FROM ai_jobs WHERE id=?", (jid,)).fetchone()


def test_tick_runs_job_done(env):
    db, conn, tmp = env
    jid = _job(conn)
    w = _worker(db, tmp, _ok)
    assert w.tick(conn) == 1
    r = _row(conn, jid)
    assert (r["state"], r["result_text"], r["tokens_out"]) == ("done", "안녕", 2)
    assert qs.worker_available(conn)


def test_concurrency_limit(env):
    db, conn, tmp = env
    for _ in range(3):
        _job(conn)
    w = _worker(db, tmp, _ok, concurrency=2)
    w.active.update({998, 999})
    assert w.tick(conn) == 0


def test_quota_pauses_and_fails_job(env):
    db, conn, tmp = env
    jid = _job(conn)
    w = _worker(db, tmp, lambda a, **k: cr.RunResult(quota=True, is_error=True, got_result=True))
    w.tick(conn)
    assert _row(conn, jid)["error_reason"] == "quota_sub"
    assert qs.is_paused(conn, w.worker_id)
    _job(conn)
    assert w.tick(conn) == 0  # paused


def test_self_pause_after_consecutive_errors(env):
    db, conn, tmp = env
    w = _worker(db, tmp, lambda a, **k: cr.RunResult(is_error=True, error_reason="no_result_rc1"))
    for _ in range(wm.SELF_PAUSE_AFTER):
        _job(conn)
        w.tick(conn)
    assert qs.is_paused(conn, w.worker_id)


def test_cancel_marks_cancelled(env):
    db, conn, tmp = env
    jid = _job(conn)
    w = _worker(db, tmp, lambda a, **k: cr.RunResult(is_error=True, error_reason="cancelled"))
    w.tick(conn)
    assert _row(conn, jid)["state"] == "cancelled"


def test_bad_input_fails_without_retry(env):
    db, conn, tmp = env
    jid = _job(conn, input_json="{not json")
    w = _worker(db, tmp, _ok)
    w.tick(conn)
    r = _row(conn, jid)
    assert r["state"] == "failed" and r["error_reason"].startswith("bad_job")


def test_read_job_builds_mcp_config_with_uid(env):
    db, conn, tmp = env
    seen = {}

    def runner(argv, **k):
        seen["argv"] = argv
        return _ok(argv)

    _job(conn, tools="read", system_ctx="ctx", input_json=json.dumps({"prompt": "q", "allowed_tools": ["get_wellness"]}))
    w = _worker(db, tmp, runner)
    w.tick(conn)
    a = seen["argv"]
    assert a[a.index("--allowedTools") + 1] == "mcp__runpulse__get_wellness"
    cfg = json.loads(open(a[a.index("--mcp-config") + 1]).read())
    assert cfg["mcpServers"]["runpulse"]["env"]["RUNPULSE_USER_ID"] == "u@x"
    assert "--system-prompt-file" in a


def test_preflight_cli_missing(env):
    db, conn, tmp = env
    assert _worker(db, tmp, _ok, claude_bin="/nonexistent/claude").preflight().startswith("cli_missing")


def test_preflight_work_dir_must_be_empty(env, tmp_path):
    db, conn, tmp = env
    fake = tmp / "claude"
    fake.write_text("#!/bin/sh\necho '2.1.310 (Claude Code)'\n")
    fake.chmod(0o755)
    w = _worker(db, tmp, _ok, claude_bin=str(fake))
    assert w.preflight() is None and w.cli_version == "2.1.310"
    (tmp / "work" / "junk").write_text("x")
    assert w.preflight().startswith("work_dir_not_empty")


def test_preflight_version_unsupported(env):
    db, conn, tmp = env
    fake = tmp / "claude"
    fake.write_text("#!/bin/sh\necho '3.0.0'\n")
    fake.chmod(0o755)
    assert _worker(db, tmp, _ok, claude_bin=str(fake)).preflight().startswith("cli_version_unsupported")
