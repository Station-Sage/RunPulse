"""export_service — 빠른 CSV, 아카이브 zip, 이력/만료, API 라우트."""
from __future__ import annotations

import csv
import io
import sqlite3
import zipfile
from datetime import datetime, timedelta

import pytest

from src.services import export_service as es
from src.utils import sync_jobs


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.executescript("""
    CREATE TABLE activity_summaries (id INTEGER PRIMARY KEY, source TEXT, matched_group_id TEXT, name TEXT,
      activity_type TEXT, start_time TEXT, distance_m REAL, duration_sec REAL, avg_pace_sec_km REAL, avg_hr INT,
      max_hr INT, avg_cadence INT, elevation_gain REAL);
    CREATE TABLE daily_wellness (date TEXT, sleep_score INT, sleep_duration_sec INT, hrv_weekly_avg REAL,
      hrv_last_night REAL, resting_hr INT, body_battery_high INT, body_battery_low INT, avg_stress INT,
      steps INT, active_calories INT, weight_kg REAL);
    CREATE TABLE metric_store (scope_type TEXT, scope_id TEXT, metric_name TEXT, numeric_value REAL,
      provider TEXT, is_primary INT);
    CREATE TABLE source_payloads (source TEXT, entity_type TEXT, entity_id TEXT, entity_date TEXT,
      fetched_at TEXT, payload TEXT);
    INSERT INTO activity_summaries VALUES (1,'strava','g1','Run','running','2026-10-01T07:00:00',10000,3000,300,150,170,180,50);
    INSERT INTO activity_summaries VALUES (2,'garmin','g1','Run','running','2026-10-01T07:00:00',10020,3001,299,151,171,181,52);
    INSERT INTO activity_summaries VALUES (3,'strava',NULL,'Old','running','2026-09-01T07:00:00',5000,1500,300,140,160,170,10);
    INSERT INTO daily_wellness VALUES ('2026-10-01',80,27000,50,48,52,90,20,30,9000,500,70);
    INSERT INTO metric_store VALUES ('daily','2026-10-01','ctl',40.5,'x',1),('daily','2026-10-01','tsb',-3,'x',1),
      ('daily','2026-10-01','ctl',99,'y',0);
    INSERT INTO source_payloads VALUES ('garmin','activity','1','2026-10-01','t','{"a":1}');
    """)
    yield c
    c.close()


def test_formatters():
    assert es.hms(3661) == "1:01:01" and es.hms(None) == ""
    assert es.pace_str(305) == "5:05/km" and es.pace_str(0) == ""


def test_parse_params():
    assert es.parse_params({"kind": "x"})[1]
    assert es.parse_params({"kind": "archive", "from": "bad"})[1]
    assert es.parse_params({"kind": "quick_load", "from": "2026-02-01", "to": "2026-01-01"})[1]
    assert es.parse_params({"kind": "quick_load", "from": "2026-01-01"})[1] is None


def test_activities_groups_and_prefers_garmin(conn):
    rows = list(es.activities_csv(conn))
    assert len(rows) == 3  # 헤더 + 그룹 g1 + 단독
    head = rows[0]
    g = dict(zip(head, rows[2]))
    assert g["sources"] == "garmin+strava" and g["distance_km"] == 10.02 and g["duration_hms"] == "0:50:01"
    assert g["distance_m_strava"] == 10000 and g["avg_hr_garmin"] == 151 and g["avg_hr_runalyze"] == ""
    assert len(list(es.activities_csv(conn, "2026-10-01", None))) == 2


def test_wellness_and_load(conn):
    w = list(es.wellness_csv(conn))
    assert w[1][3] == "7:30:00"
    ld = list(es.load_csv(conn))
    assert ld[0] == ["date", "ctl", "atl", "tsb", "acwr"] and ld[1] == ["2026-10-01", 40.5, "", -3, ""]
    assert len(list(es.load_csv(conn, "2026-11-01", None))) == 1


def test_quick_export_bom_and_parseable(conn):
    text = es.quick_export(conn, "quick_load")
    assert text.startswith("﻿")
    assert list(csv.reader(io.StringIO(text.lstrip("﻿"))))[1][1] == "40.5"


def test_build_archive(conn, tmp_path):
    info = es.build_archive(conn, tmp_path / "a.zip")
    assert info["row_counts"]["activity_summaries"] == 3 and info["row_counts"]["source_payloads"] == 1
    with zipfile.ZipFile(tmp_path / "a.zip") as z:
        names = z.namelist()
        assert "manifest.json" in names and "raw_payloads/garmin.jsonl" in names and "tables/metric_store.csv" in names


def test_job_view_expiry():
    job = sync_jobs.SyncJob(*([None] * 23))
    job.status, job.result_json = "completed", '{"expires_at": "2026-10-01T00:00:00"}'
    assert es.job_view(job, datetime(2026, 9, 30))["state"] == "done"
    assert es.job_view(job, datetime(2026, 10, 2))["state"] == "expired"


def test_routes(monkeypatch, tmp_path, conn):
    from flask import Flask

    import src.api.routes_data_export as rx
    from src.api import api_bp

    monkeypatch.setattr(sync_jobs, "_jobs_db_path", lambda uid=None: str(tmp_path / "jobs.db"))
    monkeypatch.setattr(rx, "db_path", lambda: tmp_path / "x.db")
    monkeypatch.setattr(rx, "get_current_user_id", lambda: "u")
    monkeypatch.setattr(es, "exports_dir", lambda uid: tmp_path / "exports")
    monkeypatch.setattr(es.threading, "Thread", lambda **kw: type("T", (), {"start": lambda s: None})())
    f = sqlite3.connect(tmp_path / "x.db")
    f.executescript("\n".join(conn.iterdump()))
    f.close()
    app = Flask(__name__)
    app.register_blueprint(api_bp)
    with app.test_client() as c:
        assert c.post("/api/v1/data/export", json={"kind": "nope"}).status_code == 400
        r = c.post("/api/v1/data/export", json={"kind": "quick_wellness"})
        assert r.status_code == 200 and "attachment" in r.headers["Content-Disposition"]
        r = c.post("/api/v1/data/export", json={"kind": "archive"})
        assert r.status_code == 202
        jid = r.get_json()["data"]["job_id"]
        assert c.post("/api/v1/data/export", json={"kind": "archive"}).status_code == 409
        assert c.get(f"/api/v1/data/exports/{jid}/download").status_code == 404
        (tmp_path / "exports").mkdir()
        es.build_archive(conn, tmp_path / "exports" / f"{jid}.zip")
        exp = (datetime.now() + timedelta(days=1)).isoformat(timespec="seconds")
        sync_jobs.update_job(jid, status="completed", result_json='{"filename":"a.zip","expires_at":"%s"}' % exp)
        assert c.get(f"/api/v1/data/exports/{jid}/download").status_code == 200
        assert c.get("/api/v1/data/exports").get_json()["data"]["exports"][0]["state"] == "done"
        old = (datetime.now() - timedelta(days=1)).isoformat(timespec="seconds")
        sync_jobs.update_job(jid, result_json='{"filename":"a.zip","expires_at":"%s"}' % old)
        assert c.get(f"/api/v1/data/exports/{jid}/download").status_code == 410
        assert c.get("/api/v1/data/exports/zzz/download").status_code == 404
