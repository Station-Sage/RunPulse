"""원장 기록 4경로(manual·bg·auto·cli) 테스트."""
from src.sync.ledger import finish_run, start_run
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


def test_auto_and_bg_source_path_persist():
    create_job("intervals", "2026-01-01", "2026-01-02", source_path="auto", job_id="a1")
    create_job("garmin", "2026-01-01", "2026-01-02", source_path="bg", job_id="b1")
    assert get_job("a1").source_path == "auto" and get_job("b1").source_path == "bg"
