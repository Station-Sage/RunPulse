"""claude_queue 클라이언트·상태/핑 API."""
import sqlite3

import pytest

from src.ai import claude_queue as cq
from src.ai_worker import queue_store as qs
from src.db_schema_v48 import ensure_v48


@pytest.fixture
def dbp(tmp_path):
    p = tmp_path / "running.db"
    c = sqlite3.connect(p)
    ensure_v48(c)
    c.commit()
    c.close()
    return p


CFG = {"ai": {"claude_queue": {"enabled": True, "uids": ["u1"]}}}


def test_enabled_for():
    assert cq.enabled_for(CFG, "u1")
    assert not cq.enabled_for(CFG, "u2")
    assert not cq.enabled_for({}, "u1")


def test_status_worker_down(dbp):
    c = qs.connect(dbp)
    assert cq.status(c, CFG, "u1") == {"enabled": True, "worker_up": False, "available": False}


def test_run_job_timeout_when_nobody_claims(dbp):
    r = cq.run_job(dbp, kind="ping", model="haiku", prompt="x", deadline_sec=1, queue_wait=0.3,
                   sleep=lambda s: __import__("time").sleep(0.1))
    assert not r["ok"] and r["reason"] == "cq_timeout"


def test_run_job_done(dbp):
    def fake_sleep(_):
        c = qs.connect(dbp)
        j = qs.claim(c, "w1")
        if j:
            qs.finish(c, j["id"], "done", result_text="pong")
        c.close()
    r = cq.run_job(dbp, kind="ping", model="haiku", prompt="x", deadline_sec=5, sleep=fake_sleep)
    assert r["ok"] and r["text"] == "pong"


def test_ping_api_disabled_and_origin(tmp_path, monkeypatch):
    from src import api as _api  # noqa: F401
    from src.api import routes_ai_queue as m
    from src.web.app import create_app
    p = tmp_path / "running.db"
    c = sqlite3.connect(p)
    ensure_v48(c)
    c.commit()
    c.close()
    monkeypatch.setattr(m, "db_path", lambda: p)
    monkeypatch.setattr(m, "load_config", lambda user_id=None: {})
    app = create_app()
    cl = app.test_client()
    r = cl.post("/api/v1/ai/queue/ping", headers={"Origin": "http://localhost"})
    assert r.status_code == 200 and r.get_json()["data"]["reason"] == "disabled"
    assert cl.post("/api/v1/ai/queue/ping", headers={"Origin": "http://evil.example"}).status_code == 403
