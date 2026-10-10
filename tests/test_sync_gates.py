"""sync_gates — 게이트 읽기/쓰기/백오프/사용자 분리."""
from datetime import datetime, timedelta

import pytest

from src.utils import sync_gates as sg
from src.utils import sync_jobs as sj
from src.utils import user_context as uc


@pytest.fixture(autouse=True)
def ledger(tmp_path, monkeypatch):
    monkeypatch.setattr(sj, "_jobs_db_path", lambda uid=None: str(tmp_path / f"{uid or 'default'}.db"))
    uc.set_current_job(None)


def test_no_gate_is_none():
    assert sg.wait_sec("garmin", "u") is None


def test_first_backoff_900_then_doubles_to_cap():
    assert sg.bump_backoff("garmin", user_id="u") == 900
    assert sg.bump_backoff("garmin", user_id="u") == 1800
    for _ in range(10):
        last = sg.bump_backoff("garmin", user_id="u")
    assert last == sg.MAX_BACKOFF_SEC


def test_active_gate_wait_sec():
    sg.bump_backoff("garmin", user_id="u")
    assert 0 < sg.wait_sec("garmin", "u") <= 900


def test_expired_gate_is_none_and_restarts_at_900():
    sg.bump_backoff("garmin", user_id="u")
    with sj._conn("u") as c:
        c.execute("UPDATE sync_gates SET retry_after=?",
                  ((datetime.now() - timedelta(seconds=5)).isoformat(timespec="seconds"),))
    assert sg.wait_sec("garmin", "u") is None
    assert sg.bump_backoff("garmin", user_id="u") == 900


def test_block_and_clear():
    sg.block("runalyze", 86400, reason="auth_expired", user_id="u")
    g = sg.gate("runalyze", "u")
    assert g.reason_code == "auth_expired" and g.backoff_sec == 86400
    sg.clear("runalyze", "u")
    assert sg.gate("runalyze", "u") is None


def test_job_id_recorded():
    uc.set_current_job("job-1")
    sg.bump_backoff("strava", user_id="u")
    assert sg.gate("strava", "u").job_id == "job-1"


def test_users_are_separate():
    sg.bump_backoff("garmin", user_id="a")
    assert sg.wait_sec("garmin", "b") is None
