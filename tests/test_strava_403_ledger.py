"""Strava 403(구독 필요)이 원장에 subscription_required로 남는지."""
import sqlite3
from unittest.mock import patch

import requests

from src.sync.sync_errors import SyncSourceError
from src.sync.sync_result import SyncResult
from src.utils.sync_jobs import get_latest_job


def _http403():
    r = requests.Response()
    r.status_code = 403
    return requests.HTTPError(response=r)


def test_wrapper_raises_subscription_required():
    from src.sync import strava
    res = SyncResult(source="strava", job_type="activity", status="failed",
                     error_code="subscription_required", http_status=403, last_error="403")
    with patch.object(strava._act_sync, "sync", return_value=res):
        try:
            strava.sync_activities({}, sqlite3.connect(":memory:"), 7)
        except SyncSourceError as e:
            assert (e.code, e.http_status) == ("subscription_required", 403)
        else:
            raise AssertionError("SyncSourceError 미발생")


def test_sync_source_records_failed_ledger_row(tmp_path):
    import src.sync as pkg  # noqa: F401
    import importlib.util, pathlib
    spec = importlib.util.spec_from_file_location(
        "sync_cli_mod", pathlib.Path(__file__).resolve().parent.parent / "src" / "sync.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    with patch("src.sync.strava.sync_strava", side_effect=_http403()), \
         patch("src.utils.sync_state.mark_finished"):
        res = mod._sync_source("strava", {}, tmp_path / "r.db", 7, job_id="s403", trigger="manual")
    assert res["errors"]
    j = get_latest_job("strava")
    assert (j.status, j.error_code, j.http_status, j.source_path) == (
        "failed", "subscription_required", 403, "manual")


def test_classify_403_code():
    from src.sync.sync_errors import classify_exception
    assert classify_exception(_http403()) == ("subscription_required", 403)
