"""claim_run·heartbeat — 원자적 선점, stale 정리, 동시성."""
import json
import threading
import time
from datetime import datetime, timedelta

import pytest

from src.sync import ledger
from src.utils import sync_jobs as sj


@pytest.fixture(autouse=True)
def db(tmp_path, monkeypatch):
    monkeypatch.setattr(sj, "_jobs_db_path", lambda uid=None: str(tmp_path / "j.db"))


def _claim(service="garmin", **kw):
    return ledger.claim_run(service, "2026-10-01", "2026-10-07", source_path="manual", **kw)


def _age(job_id, sec):
    t = (datetime.now() - timedelta(seconds=sec)).isoformat(timespec="seconds")
    with sj._conn() as c:
        c.execute("UPDATE sync_jobs SET updated_at=? WHERE id=?", (t, job_id))


def test_claim_empty_ledger_returns_running_row():
    jid = _claim()
    job = sj.get_job(jid)
    assert job.status == "running" and job.started_at and job.trigger == "manual"


def test_claim_blocked_by_fresh_running():
    assert _claim() is not None
    assert _claim() is None


def test_claim_other_service_independent():
    assert _claim("garmin") and _claim("strava")


def test_claim_closes_stale_and_takes_slot():
    old = _claim()
    _age(old, 700)
    new = _claim()
    assert new and new != old
    j = sj.get_job(old)
    assert j.status == "stopped" and j.error_code == "stale"


def test_claim_saves_params():
    jid = _claim(params={"mode": "full"})
    assert json.loads(sj.get_job(jid).params_json) == {"mode": "full"}


def test_concurrent_claims_single_winner():
    sj._conn().close()
    results = []
    barrier = threading.Barrier(8)

    def go():
        barrier.wait()
        results.append(_claim())

    ts = [threading.Thread(target=go) for _ in range(8)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert len([r for r in results if r]) == 1


def test_heartbeat_updates_and_stops():
    jid = _claim()
    _age(jid, 300)
    before = sj.get_job(jid).updated_at
    with ledger.heartbeat(jid, every_sec=0.05):
        time.sleep(0.3)
    assert sj.get_job(jid).updated_at > before
    _age(jid, 300)
    stale = sj.get_job(jid).updated_at
    time.sleep(0.2)
    assert sj.get_job(jid).updated_at == stale
