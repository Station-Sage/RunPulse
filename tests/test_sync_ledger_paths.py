"""원장 기록 4경로(manual·bg·auto·cli)와 fail_run 비덮어쓰기 테스트."""
from src.sync.ledger import fail_run, finish_run, start_run
from src.sync.sync_errors import SyncSourceError
from src.utils.sync_jobs import create_job, get_job


def test_cli_run_completed():
    jid = start_run("garmin", source_path="cli")
    assert get_job(jid).status == "running"
    finish_run(jid, synced=4)
    j = get_job(jid)
    assert (j.status, j.synced_count, j.source_path) == ("completed", 4, "cli")


def test_manual_failed_with_code():
    jid = start_run("strava", source_path="manual", job_id="m1")
    finish_run(jid, error=SyncSourceError("subscription_required", "403", 403))
    j = get_job("m1")
    assert (j.status, j.error_code, j.http_status, j.source_path) == (
        "failed", "subscription_required", 403, "manual")


def test_fail_run_creates_missing_row_for_timeout():
    fail_run("t1", "timeout", "타임아웃 (300초)", service="garmin", source_path="manual")
    j = get_job("t1")
    assert (j.status, j.error_code, j.service) == ("failed", "timeout", "garmin")


def test_fail_run_does_not_overwrite_child_failure():
    start_run("strava", source_path="manual", job_id="c1")
    finish_run("c1", error=SyncSourceError("auth_expired", "x", 401))
    fail_run("c1", "unknown", "stderr", service="strava")
    assert get_job("c1").error_code == "auth_expired"


def test_auto_and_bg_source_path_persist():
    create_job("intervals", "2026-01-01", "2026-01-02", source_path="auto", job_id="a1")
    create_job("garmin", "2026-01-01", "2026-01-02", source_path="bg", job_id="b1")
    assert get_job("a1").source_path == "auto" and get_job("b1").source_path == "bg"
