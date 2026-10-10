"""sync_state_retire — 미래 retry_after만 sync_gates로 이관."""
import json
from datetime import datetime, timedelta

import pytest

from src.utils import sync_gates as sg
from src.utils import sync_jobs as sj
from src.utils import sync_state_retire as rt


@pytest.fixture
def root(tmp_path, monkeypatch):
    monkeypatch.setattr(rt, "_users_dir", lambda: tmp_path)
    monkeypatch.setattr(sj, "_jobs_db_path", lambda uid=None: str(tmp_path / f"{uid or 'default'}.db"))
    (tmp_path / "u").mkdir()
    return tmp_path


def _write(root, **svc):
    (root / "u" / "sync_state.json").write_text(json.dumps(svc))


def _iso(sec):
    return (datetime.now() + timedelta(seconds=sec)).isoformat(timespec="seconds")


def test_future_retry_moved(root):
    _write(root, garmin={"retry_after": _iso(600)})
    assert rt.retire_all_users() == 1
    assert 0 < sg.wait_sec("garmin", "u") <= 600


def test_past_retry_ignored(root):
    _write(root, garmin={"retry_after": _iso(-60)})
    assert rt.retire_all_users() == 0
    assert sg.wait_sec("garmin", "u") is None


def test_idempotent_keeps_existing_gate(root):
    _write(root, garmin={"retry_after": _iso(600)})
    rt.retire_all_users()
    assert rt.retire_all_users() == 0


def test_rename_and_restore(root, monkeypatch):
    monkeypatch.setattr(rt, "RENAME_ENABLED", True)
    _write(root, garmin={"retry_after": _iso(600)})
    rt.retire_all_users()
    assert not (root / "u" / "sync_state.json").exists()
    assert rt.restore_all_users() == 1
    assert (root / "u" / "sync_state.json").exists()
