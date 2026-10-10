"""sync_ledger_query — 읽기 전용 질의."""
from datetime import datetime, timedelta

import pytest

from src.sync import ledger
from src.utils import sync_jobs as sj
from src.utils import sync_ledger_query as q


@pytest.fixture(autouse=True)
def db(tmp_path, monkeypatch):
    monkeypatch.setattr(sj, "_jobs_db_path", lambda uid=None: str(tmp_path / "j.db"))


def _set(job_id, **cols):
    sets = ", ".join(f"{k}=?" for k in cols)
    with sj._conn() as c:
        c.execute(f"UPDATE sync_jobs SET {sets} WHERE id=?", (*cols.values(), job_id))


def _ago(sec):
    return (datetime.now() - timedelta(seconds=sec)).isoformat(timespec="seconds")


def _run(service="garmin", source="manual"):
    return ledger.claim_run(service, "2026-10-01", "2026-10-02", source_path=source)


def test_busy_fresh_running():
    jid = _run()
    assert q.is_busy("garmin") and q.busy_job("garmin").id == jid


def test_busy_ignores_stale_and_does_not_write():
    jid = _run()
    _set(jid, updated_at=_ago(700))
    assert not q.is_busy("garmin")
    assert sj.get_job(jid).status == "running"


def test_busy_excludes_paused_and_rate_limited():
    jid = _run()
    _set(jid, status="paused")
    assert not q.is_busy("garmin")
    _set(jid, status="rate_limited")
    assert not q.is_busy("garmin")


def test_last_success_prefers_finished_at():
    jid = _run()
    _set(jid, status="completed", finished_at=_ago(100), updated_at=_ago(10))
    assert abs((datetime.now() - q.last_success_at("garmin")).total_seconds() - 100) < 5


def test_last_success_falls_back_to_updated_at_and_ignores_failures():
    assert q.last_success_at("garmin") is None
    jid = _run()
    _set(jid, status="failed")
    assert q.last_success_at("garmin") is None
    _set(jid, status="completed", finished_at=None, updated_at=_ago(50))
    assert q.last_success_at("garmin") is not None


def test_last_auto_run_only_auto():
    _run("garmin", "manual")
    assert q.last_auto_run() is None
    _run("strava", "auto")
    assert q.last_auto_run() is not None


def test_legacy_card_states_shape():
    jid = _run("garmin")
    _set(jid, status="completed", synced_count=3, error_code="partial_rate_limited", finished_at=_ago(5))
    st = q.legacy_card_states()
    assert set(st) == set(q.SERVICES)
    g = st["garmin"]
    assert g["last_count"] == 3 and g["last_partial"] and not g["is_running"] and g["last_sync_at"]
    assert set(g) >= {"cooldown_sec", "cooldown_msg", "last_error"}
