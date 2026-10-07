"""원장 스키마(ensure_ledger) 멱등성·구버전 업그레이드 테스트."""
import dataclasses
import sqlite3

from src.utils import sync_jobs_schema as sch
from src.utils.sync_jobs import SyncJob


def _cols(path):
    with sqlite3.connect(path) as c:
        return [r[1] for r in c.execute("PRAGMA table_info(sync_jobs)")]


def test_ensure_ledger_idempotent(tmp_path):
    p = str(tmp_path / "j.db")
    for _ in range(2):
        sch._ensured.discard(p)
        c = sqlite3.connect(p)
        sch.ensure_ledger(c, p)
        c.close()
    assert {"error_code", "http_status", "source_path"} <= set(_cols(p))


def test_old_15_column_db_upgraded(tmp_path):
    p = str(tmp_path / "old.db")
    c = sqlite3.connect(p)
    c.execute(sch.CREATE_SQL)
    c.execute(
        "INSERT INTO sync_jobs VALUES ('a','strava','2026-01-01','2026-01-02',7,NULL,'completed',0,1,3,0,'t','t',NULL,NULL)"
    )
    c.commit()
    sch._ensured.discard(p)
    sch.ensure_ledger(c, p)
    row = c.execute("SELECT id, error_code, source_path FROM sync_jobs").fetchone()
    c.close()
    assert row == ("a", None, None)
    assert len(_cols(p)) == 22


def test_syncjob_has_22_fields():
    assert len(dataclasses.fields(SyncJob)) == 22


def test_cleanup_all_users_closes_only_stale(tmp_path, monkeypatch):
    from datetime import datetime, timedelta
    import src.db_setup as dbs
    from src.utils import sync_jobs as sj
    monkeypatch.setattr(dbs, "_PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(sj, "_jobs_db_path", lambda uid=None: str(tmp_path / "data" / "users" / (uid or "default") / "sync_jobs.db"))
    old = (datetime.now() - timedelta(hours=1)).isoformat(timespec="seconds")
    new = datetime.now().isoformat(timespec="seconds")
    for uid, ts in (("a@x", old), ("b@x", new)):
        d = tmp_path / "data" / "users" / uid
        d.mkdir(parents=True)
        with sj._conn(uid) as c:
            c.execute("INSERT INTO sync_jobs (id,service,from_date,to_date,window_days,status,completed_days,"
                      "total_days,synced_count,req_count,created_at,updated_at) "
                      "VALUES ('j','garmin','2026-01-01','2026-01-02',7,'running',0,1,0,0,?,?)", (ts, ts))
    assert sj.cleanup_stale_running_jobs_all_users(600) == 1
    with sj._conn("a@x") as c:
        assert c.execute("select status from sync_jobs").fetchone()[0] == "stopped"
    with sj._conn("b@x") as c:
        assert c.execute("select status from sync_jobs").fetchone()[0] == "running"


def test_update_job_stamps_started_and_finished(tmp_path):
    from src.utils import sync_jobs as sj
    job = sj.create_job("strava", "2026-01-01", "2026-01-02", source_path="manual")
    assert job.trigger == "manual" and job.started_at is None
    sj.update_job(job.id, status="running")
    first = sj.get_job(job.id).started_at
    assert first
    sj.update_job(job.id, status="running")
    assert sj.get_job(job.id).started_at == first
    sj.update_job(job.id, status="completed", counts_json='{"activities": 2}')
    done = sj.get_job(job.id)
    assert done.finished_at and done.counts_json == '{"activities": 2}'
