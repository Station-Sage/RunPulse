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
    assert len(_cols(p)) == 18


def test_syncjob_has_18_fields():
    assert len(dataclasses.fields(SyncJob)) == 18
