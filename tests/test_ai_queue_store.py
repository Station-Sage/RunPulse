"""ai_worker.queue_store + db_schema_v48 — claim 경합·정체 회수·만료·일시정지·CHECK 제약."""
import sqlite3
import threading

import pytest

from src.ai_worker import queue_store as q
from src.db_schema_v48 import ensure_v48


@pytest.fixture
def db(tmp_path):
    p = tmp_path / "r.db"
    c = q.connect(p)
    c.execute("PRAGMA journal_mode=WAL")
    ensure_v48(c)
    yield p, c
    c.close()


def _job(c, **kw):
    return q.enqueue(c, kind=kw.pop("kind", "ping"), model="haiku", input_json="{}", **kw)


def test_v48_idempotent_and_checks(db):
    _, c = db
    ensure_v48(c)
    names = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"ai_jobs", "ai_sessions", "ai_worker_state", "ai_outputs"} <= names
    with pytest.raises(sqlite3.IntegrityError):
        c.execute("INSERT INTO ai_jobs(kind,model,input_json,created_at,expires_at) VALUES('bad','m','{}','a','b')")
    with pytest.raises(sqlite3.IntegrityError):
        c.execute("INSERT INTO ai_jobs(kind,model,input_json,tools,created_at,expires_at)"
                  " VALUES('ping','m','{}','write','a','b')")


def test_claim_order_priority_then_id(db):
    _, c = db
    a = _job(c, priority=5)
    b = _job(c, priority=1)
    d = _job(c, priority=5)
    assert [q.claim(c, "w")["id"] for _ in range(3)] == [b, a, d]
    assert q.claim(c, "w") is None


def test_claim_sets_running_and_attempts(db):
    _, c = db
    _job(c)
    j = q.claim(c, "w1")
    assert j["state"] == "running" and j["worker_id"] == "w1" and j["attempts"] == 1 and j["queue_ms"] >= 0


def test_claim_race_no_double_claim(db):
    p, _ = db
    c0 = q.connect(p)
    for _ in range(20):
        _job(c0)
    got, lock = [], threading.Lock()

    def run(name):
        c = q.connect(p)
        while (j := q.claim(c, name)):
            with lock:
                got.append(j["id"])
        c.close()

    ts = [threading.Thread(target=run, args=(f"w{i}",)) for i in range(4)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert sorted(got) == sorted(set(got)) and len(got) == 20


def test_claim_skips_expired_and_cancelled(db):
    _, c = db
    old = q.now_iso()
    _job(c, now=old, ttl_sec=1)
    x = _job(c)
    c.execute("UPDATE ai_jobs SET cancel_requested=1 WHERE id=?", (x,))
    later = q._shift(old, 5)
    assert q.claim(c, "w", now=later) is None
    assert q.expire_queued(c, now=later) == 2
    assert {r[0] for r in c.execute("SELECT state FROM ai_jobs")} == {"expired", "cancelled"}


def test_finish_only_from_running(db):
    _, c = db
    i = _job(c)
    assert not q.finish(c, i, "done", result_text="x")
    q.claim(c, "w")
    assert q.finish(c, i, "done", result_text="ok", tokens_in=3)
    assert not q.finish(c, i, "failed", error_reason="late")
    assert c.execute("SELECT state,result_text,run_ms FROM ai_jobs").fetchone()[:2] == ("done", "ok")
    with pytest.raises(ValueError):
        q.finish(c, i, "running")


def test_recover_stale_requeue_then_fail(db):
    _, c = db
    i = _job(c)
    t0 = q.now_iso()
    q.claim(c, "w", now=t0)
    assert q.recover_stale(c, now=q._shift(t0, 30)) == {"requeued": 0, "failed": 0}
    assert q.recover_stale(c, now=q._shift(t0, 90)) == {"requeued": 1, "failed": 0}
    q.claim(c, "w", now=t0)
    assert q.recover_stale(c, now=q._shift(t0, 90)) == {"requeued": 0, "failed": 1}
    r = c.execute("SELECT state,error_reason FROM ai_jobs WHERE id=?", (i,)).fetchone()
    assert tuple(r) == ("failed", "stale")


def test_recover_on_startup_by_worker_id(db):
    _, c = db
    _job(c)
    _job(c)
    q.claim(c, "me")
    q.claim(c, "other")
    assert q.recover_stale(c, worker_id="me")["requeued"] == 1
    assert c.execute("SELECT count(*) FROM ai_jobs WHERE state='running'").fetchone()[0] == 1


def test_heartbeat_keeps_alive(db):
    _, c = db
    i = _job(c)
    t0 = q.now_iso()
    q.claim(c, "w", now=t0)
    q.heartbeat(c, [i], now=q._shift(t0, 80))
    assert q.recover_stale(c, now=q._shift(t0, 90)) == {"requeued": 0, "failed": 0}


def test_progress_and_cancel_flag(db):
    _, c = db
    i = _job(c)
    q.claim(c, "w")
    q.update_progress(c, i, progress_json='{"s":1}', partial_text="ab")
    q.update_progress(c, i, partial_text="abc")
    assert tuple(c.execute("SELECT progress_json,partial_text FROM ai_jobs").fetchone()) == ('{"s":1}', "abc")
    assert not q.cancel_requested(c, i)
    c.execute("UPDATE ai_jobs SET cancel_requested=1")
    assert q.cancel_requested(c, i)


def test_pause_and_worker_available(db):
    _, c = db
    t0 = q.now_iso()
    assert not q.worker_available(c, now=t0)
    q.upsert_worker_state(c, "w", pid=1, cli_version="2.1", active_jobs=0, started_at=t0, now=t0)
    assert q.worker_available(c, now=q._shift(t0, 10))
    assert not q.worker_available(c, now=q._shift(t0, 30))
    q.set_paused(c, "w", q._shift(t0, 900), "quota")
    assert q.is_paused(c, "w", now=t0) and not q.worker_available(c, now=t0)
    assert not q.is_paused(c, "w", now=q._shift(t0, 901))


def test_purge_bodies(db):
    _, c = db
    i = _job(c)
    t0 = q.now_iso()
    q.claim(c, "w", now=t0)
    q.finish(c, i, "done", result_text="secret", now=t0)
    assert q.purge_bodies(c, now=q._shift(t0, 3 * 86400)) == 0
    assert q.purge_bodies(c, now=q._shift(t0, 8 * 86400)) == 1
    assert c.execute("SELECT result_text FROM ai_jobs").fetchone()[0] is None
