"""manual_sync_service — 원장 선점·결과 판독 단위 테스트."""
from __future__ import annotations

import subprocess
from types import SimpleNamespace
from unittest.mock import patch

from src.services import manual_sync_service as ms


def _job(status="completed", count=3, code=None, err=None):
    return SimpleNamespace(status=status, synced_count=count, error_code=code, last_error=err)


def _proc(rc=0, err=""):
    return SimpleNamespace(returncode=rc, stdout="", stderr=err)


def test_run_one_skips_when_slot_taken():
    with patch.object(ms, "claim_run", return_value=None):
        r = ms.run_one("garmin", 3, "u")
    assert r["skipped"] and r["reason"] == "running"


def test_run_one_reads_count_from_ledger():
    with patch.object(ms, "claim_run", return_value="j1"), \
         patch.object(ms.subprocess, "run", return_value=_proc()), \
         patch.object(ms, "get_job", return_value=_job(count=5)):
        r = ms.run_one("strava", 3, "u")
    assert r["ok"] and r["count"] == 5 and r["partial"] is False


def test_run_one_partial_flag():
    with patch.object(ms, "claim_run", return_value="j1"), \
         patch.object(ms.subprocess, "run", return_value=_proc()), \
         patch.object(ms, "get_job", return_value=_job(count=0, code="partial_rate_limited")):
        r = ms.run_one("strava", 3, "u")
    assert r["partial"] is True and r["ok"] is False


def test_run_one_nonzero_exit_records_failure():
    with patch.object(ms, "claim_run", return_value="j1"), \
         patch.object(ms.subprocess, "run", return_value=_proc(1, "boom")), \
         patch.object(ms, "fail_run") as fr:
        r = ms.run_one("garmin", 3, "u")
    assert not r["ok"] and r["error"] == "boom"
    fr.assert_called_once()


def test_run_one_timeout_records_failure():
    with patch.object(ms, "claim_run", return_value="j1"), \
         patch.object(ms.subprocess, "run", side_effect=subprocess.TimeoutExpired("x", 1)), \
         patch.object(ms, "fail_run") as fr:
        r = ms.run_one("garmin", 3, "u")
    assert "타임아웃" in r["error"] and fr.call_args.args[1] == "timeout"


def test_precheck_blocks_on_retry_after():
    with patch("src.utils.sync_gates.wait_sec", return_value=120):
        days, guard, blocked = ms.precheck("garmin", "u", None, 3)
    assert blocked["reason"] == "retry_after" and blocked["retry_after_sec"] == 120 and days is None
