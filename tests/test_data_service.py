"""data_service·GET /data/{summary,sources,runs} — 소스 카드·상세·개요·기록."""
from __future__ import annotations

import sqlite3

import pytest
from flask import Flask

from src.api import api_bp
from src.db_setup import create_tables, migrate_db
from src.services import data_service as svc, sync_state_service
from src.utils.sync_jobs import SyncJob

CONFIG = {"garmin": {"email": "x"}, "sync_sources": ["garmin"]}


def _job(i, service, status, counts=None, error=None):
    return SyncJob(f"j{i}", service, "2026-10-01", "2026-10-07", 14, None, status, 7, 7, 3, 0,
                   f"2026-10-0{i}T10:00:00", f"2026-10-0{i}T10:05:00", None, None, error_code=error,
                   counts_json=counts, trigger="manual", finished_at=f"2026-10-0{i}T10:05:00")


@pytest.fixture
def conn(monkeypatch):
    c = sqlite3.connect(":memory:")
    create_tables(c)
    migrate_db(c)
    c.execute("INSERT INTO activity_summaries (source, source_id, activity_type, start_time) VALUES"
              " ('garmin','1','running','2026-10-01T07:00:00'),('garmin','2','running','2026-09-15T07:00:00'),"
              " ('strava','9','running','2026-10-02T07:00:00')")
    c.execute("INSERT INTO source_payloads (source, entity_type, entity_id, entity_date, payload)"
              " VALUES ('garmin','wellness_sleep','a','2026-10-01','{}'),('garmin','wellness_hrv','b','2026-10-01','{}')")
    c.execute("INSERT INTO daily_wellness (date) VALUES ('2026-10-01')")
    jobs = [_job(3, "garmin", "failed", error="upstream_5xx"),
            _job(2, "garmin", "completed", counts='{"activities": 2}'), _job(1, "strava", "completed")]
    for mod in (svc, sync_state_service):
        monkeypatch.setattr(mod, "list_recent_jobs",
                            lambda p=None, limit=10, _j=jobs: [j for j in _j if p in (None, j.service)][:limit])
    yield c
    c.close()


def test_sources_cards_have_two_axes_and_counts(conn):
    by = {s["provider"]: s for s in svc.sources(conn, CONFIG)}
    assert by["garmin"]["enabled"] and by["garmin"]["activity_count"] == 2
    assert by["strava"]["connection"] == "not_connected" and by["strava"]["activity_count"] == 1


def test_source_detail_counts_and_coverage(conn):
    d = svc.source_detail(conn, CONFIG, "garmin", today="2026-10-07")
    assert d["counts"]["activities"] == 2 and d["counts"]["wellness_days"] == 1
    assert len(d["coverage"]["months"]) == 12 and d["coverage"]["months"][-1] == {"month": "2026-10", "count": 1}
    assert d["coverage"]["first"] == "2026-09-15" and d["coverage"]["last"] == "2026-10-01"
    assert [r["id"] for r in d["recent_runs"]] == ["j3", "j2"]


def test_source_detail_unknown_is_none(conn):
    assert svc.source_detail(conn, CONFIG, "coros") is None


def test_runs_parse_counts_and_filter_errors(conn):
    all_runs = svc.runs()
    assert all_runs[1]["counts"] == {"activities": 2} and all_runs[0]["error_code"] == "upstream_5xx"
    assert [r["id"] for r in svc.runs(errors_only=True)] == ["j3"]
    assert svc.runs(limit=0)[0]["id"] == "j3"


def test_summary_tiles(conn):
    s = svc.summary(conn, CONFIG)
    assert s["activities"] == 3 and s["wellness_days"] == 1
    assert s["period"] == {"first": "2026-09-15", "last": "2026-10-02"} and s["storage_bytes"] > 0
    assert len(s["recent_runs"]) == 3


def test_summary_empty_db_does_not_raise():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    assert svc.summary(c, {})["activities"] == 0


@pytest.fixture
def client(tmp_path, monkeypatch, conn):
    db = tmp_path / "running.db"
    conn.commit()
    conn.execute("VACUUM INTO ?", (str(db),))
    import src.api.routes_data as rd
    monkeypatch.setattr(rd, "db_path", lambda: db)
    monkeypatch.setattr(rd, "get_current_user_id", lambda: "u")
    monkeypatch.setattr(rd, "load_config", lambda user_id=None: CONFIG)
    app = Flask(__name__)
    app.register_blueprint(api_bp)
    with app.test_client() as c:
        yield c


def test_endpoints(client):
    assert client.get("/api/v1/data/summary").get_json()["data"]["activities"] == 3
    assert len(client.get("/api/v1/data/sources").get_json()["data"]["sources"]) == 4
    assert client.get("/api/v1/data/sources/garmin").get_json()["data"]["counts"]["activities"] == 2
    assert client.get("/api/v1/data/sources/coros").status_code == 404
    assert [r["id"] for r in client.get("/api/v1/data/runs?errors_only=1").get_json()["data"]["runs"]] == ["j3"]
    assert client.get("/api/v1/data/runs?provider=x").status_code == 400
