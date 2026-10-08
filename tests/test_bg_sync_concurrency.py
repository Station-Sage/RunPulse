"""bg_sync — 동시 시작 중복 방지, (user, service) 키 분리."""
from __future__ import annotations

import threading
from types import SimpleNamespace

from src.web import bg_sync


class _FakeThread:
    def __init__(self, *a, **k):
        self.started = False

    def start(self):
        self.started = True

    def is_alive(self):
        return True


def _setup(monkeypatch):
    bg_sync._threads.clear()
    n = {"c": 0}

    def create(service, f, t, source_path="bg"):
        n["c"] += 1
        return SimpleNamespace(id=f"job{n['c']}")
    monkeypatch.setattr(bg_sync, "create_job", create)
    monkeypatch.setattr(bg_sync, "BgSyncThread", _FakeThread)
    monkeypatch.setattr(bg_sync, "get_active_job", lambda s: SimpleNamespace(id="job1"))
    return n


def test_concurrent_start_creates_one_job(monkeypatch):
    n = _setup(monkeypatch)
    results = []
    barrier = threading.Barrier(6)

    def go():
        barrier.wait()
        results.append(bg_sync._start_or_existing("garmin", "2026-10-01", "2026-10-07", {}, "u"))
    ts = [threading.Thread(target=go) for _ in range(6)]
    [t.start() for t in ts]; [t.join() for t in ts]
    assert n["c"] == 1
    assert sum(1 for _, created in results if created) == 1
    bg_sync._threads.clear()


def test_different_users_do_not_collide(monkeypatch):
    n = _setup(monkeypatch)
    a = bg_sync._start_or_existing("garmin", "a", "b", {}, "u1")
    b = bg_sync._start_or_existing("garmin", "a", "b", {}, "u2")
    assert a[1] and b[1] and n["c"] == 2
    bg_sync._threads.clear()


def test_create_failure_releases_slot(monkeypatch):
    _setup(monkeypatch)
    monkeypatch.setattr(bg_sync, "create_job", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("x")))
    try:
        bg_sync._start_or_existing("garmin", "a", "b", {}, "u")
    except RuntimeError:
        pass
    assert ("u", "garmin") not in bg_sync._threads


def test_cancel_job_marks_cancelled_with_reason(monkeypatch):
    jobs = [SimpleNamespace(id="j1")]
    calls = []
    monkeypatch.setattr(bg_sync, "get_active_job", lambda s: jobs[0] if jobs else None)
    monkeypatch.setattr(bg_sync, "update_job", lambda jid, **kw: (calls.append((jid, kw)), jobs.clear()))
    assert bg_sync.cancel_job("strava", "u") == ["j1"]
    assert calls == [("j1", {"status": "cancelled", "error_code": "source_disabled"})]


def test_cancel_job_without_active_job_is_noop(monkeypatch):
    monkeypatch.setattr(bg_sync, "get_active_job", lambda s: None)
    assert bg_sync.cancel_job("strava", "u") == []


def test_resume_ignores_cancelled_job(monkeypatch):
    monkeypatch.setattr(bg_sync, "get_active_job", lambda s: None)
    assert bg_sync.resume_job("strava", {}, "u") is False
